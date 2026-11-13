using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using LibreHardwareMonitor.Hardware;

namespace DeckEdgeDesktop
{
    // Le moteur utilise la bibliothèque LHM, sans exécuter son application graphique.
    // Seul ce mode de DeckEdge demande les droits matériels ; le Studio reste normal.
    internal static class SensorWorker
    {
        delegate bool WindowVisitor(IntPtr window, IntPtr data);
        [DllImport("user32.dll")] static extern bool EnumWindows(WindowVisitor visitor, IntPtr data);
        [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window, out uint process);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr window, StringBuilder title, int size);
        [DllImport("user32.dll")] static extern bool PostMessage(IntPtr window, uint message, IntPtr wparam, IntPtr lparam);

        internal static void Run(string pipeName, int parentId)
        {
            Computer computer = null;
            try {
                using (var parent = Process.GetProcessById(parentId))
                using (var pipe = new NamedPipeClientStream(".", pipeName, PipeDirection.Out)) {
                    pipe.Connect(15000);
                    using (var writer = new StreamWriter(pipe, new UTF8Encoding(false)) { AutoFlush = true }) {
                        CloseLegacyMonitorOnce();
                        computer = new Computer {
                            IsCpuEnabled = true, IsGpuEnabled = true, IsMemoryEnabled = true,
                            IsMotherboardEnabled = true, IsStorageEnabled = true, IsNetworkEnabled = true,
                            IsBatteryEnabled = true, IsControllerEnabled = true, IsPsuEnabled = true
                        };
                        computer.Open();
                        bool elevated = new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator);
                        var json = new JavaScriptSerializer { MaxJsonLength = 4 * 1024 * 1024 };
                        Program.Log("Moteur de capteurs intégré ouvert (administrateur=" + elevated + ").");
                        while (!parent.HasExited) {
                            var sensors = new List<object>();
                            foreach (var hardware in computer.Hardware) Collect(hardware, sensors);
                            writer.WriteLine(json.Serialize(new { type = "sensor_snapshot", elevated = elevated, sensors = sensors }));
                            Thread.Sleep(1000);
                        }
                    }
                }
            } catch (IOException) { /* Fermeture du canal par DeckEdge : arrêt normal. */ }
            catch (Exception ex) { Program.Log("Moteur de capteurs: " + ex); }
            finally {
                if (computer != null) { try { computer.Close(); } catch (Exception ex) { Program.Log("Fermeture capteurs: " + ex.Message); } }
                Program.Log("Moteur de capteurs intégré arrêté.");
            }
        }

        static void CloseLegacyMonitorOnce()
        {
            // Migration de l'ancien poste de développement uniquement.
            if (Directory.Exists(Path.Combine(Program.Project, "runtime"))) return;
            string marker = Path.Combine(Program.Project, ".integrated-monitoring");
            if (File.Exists(marker)) return;
            string legacy = Path.GetFullPath(Path.Combine(Program.Project, "..", "LibreHardwareMonitor", "LibreHardwareMonitor.exe"));
            bool completed = true;
            foreach (var process in Process.GetProcessesByName("LibreHardwareMonitor")) {
                using (process) {
                    try {
                        if (!String.Equals(process.MainModule.FileName, legacy, StringComparison.OrdinalIgnoreCase)) continue;
                        uint legacyId = (uint)process.Id;
                        EnumWindows(delegate(IntPtr window, IntPtr data) {
                            uint pid; GetWindowThreadProcessId(window, out pid);
                            if (pid != legacyId) return true;
                            var title = new StringBuilder(256); GetWindowText(window, title, title.Capacity);
                            if (title.ToString().IndexOf("Libre", StringComparison.OrdinalIgnoreCase) >= 0)
                                PostMessage(window, 0x0010, IntPtr.Zero, IntPtr.Zero);
                            return true;
                        }, IntPtr.Zero);
                        completed = process.WaitForExit(4000) && completed;
                    } catch (Exception ex) { completed = false; Program.Log("Migration ancienne instance LHM: " + ex.Message); }
                }
            }
            if (completed) File.WriteAllText(marker, "Moteur intégré DeckEdge.\n");
        }

        static void Collect(IHardware hardware, List<object> sensors)
        {
            try { hardware.Update(); }
            catch (Exception ex) { Program.Log("Lecture " + hardware.Name + ": " + ex.Message); return; }
            foreach (var sensor in hardware.Sensors) {
                float? value = sensor.Value;
                if (value.HasValue && (Single.IsNaN(value.Value) || Single.IsInfinity(value.Value))) value = null;
                sensors.Add(new {
                    id = sensor.Identifier.ToString(), name = sensor.Name,
                    hardware = hardware.Name, hardware_type = hardware.HardwareType.ToString(),
                    type = sensor.SensorType.ToString(), unit = Unit(sensor.SensorType.ToString()), value = value
                });
            }
            foreach (var child in hardware.SubHardware) Collect(child, sensors);
        }

        static string Unit(string type)
        {
            switch (type) {
                case "Temperature": return "°C";
                case "Load": case "Control": case "Level": return "%";
                case "Clock": return "MHz";
                case "Frequency": return "Hz";
                case "Fan": return "tr/min";
                case "Power": return "W";
                case "Voltage": return "V";
                case "Current": return "A";
                case "Data": return "Go";
                case "SmallData": return "Mo";
                case "Throughput": return "o/s";
                case "Flow": return "L/h";
                case "Energy": return "mWh";
                case "TimeSpan": return "s";
                default: return "";
            }
        }
    }

    internal sealed class SensorBridge : IDisposable
    {
        NamedPipeServerStream pipe;
        bool disposed;
        internal bool IsRunning { get { return !disposed && pipe != null; } }

        internal async Task StartAsync(Action<string> receive, bool fullAccess)
        {
            string name = "DeckEdge-sensors-" + Guid.NewGuid().ToString("N");
            var security = new PipeSecurity();
            security.SetAccessRuleProtection(true, false);
            security.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.NetworkSid, null), PipeAccessRights.FullControl, AccessControlType.Deny));
            security.AddAccessRule(new PipeAccessRule(WindowsIdentity.GetCurrent().User, PipeAccessRights.FullControl, AccessControlType.Allow));
            pipe = new NamedPipeServerStream(name, PipeDirection.In, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous, 65536, 0, security);
            var readerTask = Task.Run(async delegate {
                try {
                    await pipe.WaitForConnectionAsync();
                    using (var reader = new StreamReader(pipe, Encoding.UTF8)) {
                        string line;
                        while (!disposed && (line = await reader.ReadLineAsync()) != null) receive(line);
                    }
                } catch (Exception ex) { if (!disposed) Program.Log("Canal capteurs: " + ex.Message); }
                finally { Dispose(); }
            });
            try {
                string arguments = "--sensors " + name + " " + Process.GetCurrentProcess().Id;
                try {
                    await Task.Run(() => {
                        using (var worker = Process.Start(new ProcessStartInfo(ApplicationPath(), arguments) {
                            UseShellExecute = true, Verb = fullAccess ? "runas" : "", WindowStyle = ProcessWindowStyle.Hidden,
                            WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory
                        })) { }
                    });
                } catch (Win32Exception ex) {
                    if (ex.NativeErrorCode != 1223) throw;
                    Program.Log("Élévation des capteurs annulée : mesures disponibles sans droits administrateur.");
                    using (var worker = Process.Start(new ProcessStartInfo(ApplicationPath(), arguments) {
                        UseShellExecute = false, CreateNoWindow = true,
                        WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory
                    })) { }
                }
                // Une connexion absente ne doit pas laisser un canal bloqué indéfiniment.
                ExpireUnconnectedPipe();
            } catch { Dispose(); throw; }
        }

        static string ApplicationPath() { return Process.GetCurrentProcess().MainModule.FileName; }

        async void ExpireUnconnectedPipe()
        {
            await Task.Delay(20000);
            if (disposed) return;
            try { if (!pipe.IsConnected) Dispose(); } catch (ObjectDisposedException) { }
        }

        public void Dispose()
        {
            if (disposed) return;
            disposed = true;
            if (pipe != null) { try { pipe.Dispose(); } catch { } }
        }
    }
}
