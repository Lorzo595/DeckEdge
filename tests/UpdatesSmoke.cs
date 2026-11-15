using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;

namespace DeckEdgeDesktop
{
    internal static class UpdatesSmoke
    {
        static int checks;
        static void Assert(bool value, string message) { checks++; if (!value) throw new Exception(message); }
        static void Reject(Action action, string message) { bool rejected = false; try { action(); } catch (InvalidDataException) { rejected = true; } Assert(rejected, message); }
        static string Hash(string file) { using (var hash = SHA256.Create()) using (var stream = File.OpenRead(file)) return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
        static AppRelease Release(string tag, bool preview)
        {
            return new AppRelease { tag_name = tag, prerelease = preview, assets = new[] {
                new ReleaseAsset { name = "DeckEdge-" + tag.Substring(1) + "-Portable-x64.zip", size = 100, browser_download_url = "https://github.com/Lorzo595/DeckEdge/releases/download/" + tag + "/DeckEdge-" + tag.Substring(1) + "-Portable-x64.zip" },
                new ReleaseAsset { name = "SHA256SUMS.txt", size = 100 }
            } };
        }
        static string Archive(string root, string name, Dictionary<string, string> files)
        {
            string path = Path.Combine(root, name);
            using (var zip = ZipFile.Open(path, ZipArchiveMode.Create)) foreach (var file in files)
                using (var writer = new StreamWriter(zip.CreateEntry(file.Key).Open())) writer.Write(file.Value);
            return path;
        }
        internal static Dictionary<string, string> Payload()
        {
            return new Dictionary<string, string> {
                {"DeckEdge/DeckEdge.exe", "new executable"}, {"DeckEdge/VERSION", "0.1.5"},
                {"DeckEdge/desktop_backend.py", "new server"}, {"DeckEdge/portable.flag", "new flag"}, {"DeckEdge/runtime/python.exe", "new runtime"},
                {"DeckEdge/new-file.txt", "new file"}
            };
        }
        static Dictionary<string, string> Snapshot(string directory)
        {
            return Directory.GetFiles(directory, "*", SearchOption.AllDirectories).ToDictionary(f => f.Substring(directory.Length), Hash);
        }
        [STAThread]
        static void Main(string[] args)
        {
            string root = args[0]; Directory.CreateDirectory(root);
            var stable = Release("v1.0.0", false); var preview = Release("v1.1.0", true);
            var draft = Release("v9.0.0", false); draft.draft = true;
            var missing = Release("v8.0.0", false); missing.assets = new ReleaseAsset[0];
            string json = new JavaScriptSerializer().Serialize(new[] { stable, preview, draft, missing });
            Assert(UpdateEngine.SelectRelease(json, true).tag_name == "v1.1.0", "Preview selection");
            Assert(UpdateEngine.SelectRelease(json, false).tag_name == "v1.0.0", "Stable selection");
            Assert(UpdateEngine.SelectRelease("[]", true) == null, "Empty release feed");
            Assert(UpdateEngine.ParseVersion("v0.1.5") == new Version(0, 1, 5, 0), "Numeric version");
            Assert(UpdateEngine.ParseVersion("v1.2.3-rc.1") == null, "Unsupported tag");
            Assert(UpdateEngine.AssetUri(preview, preview.Package).Host == "github.com", "Official download");
            preview.Package.browser_download_url = "https://example.com/update.zip";
            Reject(() => UpdateEngine.AssetUri(preview, preview.Package), "Foreign asset accepted");
            foreach (string bad in new[] { "../escape", "DeckEdge/../escape", "DeckEdge/data/config.json", "DeckEdge/.phone-key", "DeckEdge/config.json", "DeckEdge/runtime/file:stream", "DeckEdge/C:/escape", "DeckEdge/runtime/../outside", "DeckEdge/path./file", "DeckEdge//file" })
                Reject(() => UpdateEngine.SafeRelative(bad), "Unsafe path accepted: " + bad);
            string archive = Archive(root, "good.zip", Payload());
            string hash = Hash(archive);
            Assert(UpdateEngine.ExpectedHash(hash + "  package.zip\r\n", "package.zip") == hash, "Checksum parsed");
            Reject(() => UpdateEngine.ExpectedHash(hash + "  package.zip\n" + hash + "  package.zip\n", "package.zip"), "Duplicate checksum accepted");
            Reject(() => UpdateEngine.ExpectedHash(hash + "  other.zip\n", "package.zip"), "Missing checksum accepted");
            UpdateEngine.VerifyHash(archive, hash);
            Reject(() => UpdateEngine.VerifyHash(archive, new string('0', 64)), "Bad hash accepted");
            string payload = Path.Combine(root, "payload");
            UpdateEngine.Extract(archive, payload, "0.1.5", CancellationToken.None);
            Reject(() => UpdateEngine.Extract(archive, Path.Combine(root, "wrong-version"), "0.1.6", CancellationToken.None), "Wrong package version accepted");
            foreach (var extra in new[] { "DeckEdge/../escape.txt", "DeckEdge/data/config.json", "DeckEdge/deckedge.exe" }) {
                var files = Payload(); files.Add(extra, "bad");
                string invalid = Archive(root, Guid.NewGuid() + ".zip", files);
                Reject(() => UpdateEngine.Extract(invalid, Path.Combine(root, Guid.NewGuid().ToString()), "0.1.5", CancellationToken.None), "Unsafe archive accepted");
            }
            foreach (bool portable in new[] { false, true }) {
                string target = Path.Combine(root, portable ? "portable with spaces" : "installed with spaces"); Directory.CreateDirectory(target);
                File.WriteAllText(Path.Combine(target, "DeckEdge.exe"), "old executable"); File.WriteAllText(Path.Combine(target, "desktop_backend.py"), "old server");
                File.WriteAllText(Path.Combine(target, "VERSION"), "0.1.4");
                if (portable) File.WriteAllText(Path.Combine(target, "portable.flag"), "keep original flag");
                Directory.CreateDirectory(Path.Combine(target, "data"));
                File.WriteAllText(Path.Combine(target, "data/config.json"), "private profile"); File.WriteAllText(Path.Combine(target, "data/.phone-key"), "private phone key");
                File.WriteAllText(Path.Combine(target, "my-file.txt"), "unmanaged file");
                var before = Snapshot(target);
                var plan = new UpdatePlan { Target = target, Version = "0.1.5", Portable = portable };
                plan.DataDirectory = Path.Combine(target, "runtime");
                Reject(() => UpdateEngine.Apply(plan, payload, Path.Combine(root, Guid.NewGuid().ToString()), null), "Custom data overlap accepted");
                Assert(before.All(f => Hash(Path.Combine(target, f.Key.TrimStart(Path.DirectorySeparatorChar))) == f.Value), "Custom data rejection changed existing files");
                plan.DataDirectory = Path.Combine(target, "data");
                bool failed = false;
                try { UpdateEngine.Apply(plan, payload, Path.Combine(root, Guid.NewGuid().ToString()), count => { if (count == 3) throw new IOException("Simulated write failure"); }); }
                catch (IOException) { failed = true; }
                Assert(failed, "Write failure not raised");
                var after = Snapshot(target);
                Assert(before.Count == after.Count && before.All(f => after.ContainsKey(f.Key) && after[f.Key] == f.Value), "Rollback did not restore all files");
                UpdateEngine.Apply(plan, payload, Path.Combine(root, Guid.NewGuid().ToString()), null);
                Assert(File.ReadAllText(Path.Combine(target, "DeckEdge.exe")) == "new executable", "Executable not replaced");
                Assert(File.ReadAllText(Path.Combine(target, "data/config.json")) == "private profile", "Profile changed");
                Assert(File.ReadAllText(Path.Combine(target, "data/.phone-key")) == "private phone key", "Phone key changed");
                Assert(File.ReadAllText(Path.Combine(target, "my-file.txt")) == "unmanaged file", "Unmanaged file changed");
                Assert(File.Exists(Path.Combine(target, "portable.flag")) == portable, "Edition changed during update");
                if (portable) Assert(File.ReadAllText(Path.Combine(target, "portable.flag")) == "keep original flag", "Portable marker overwritten");
                Reject(() => UpdateEngine.ValidateTarget(plan), "Same-version update accepted");
            }
            var cts = new CancellationTokenSource(); cts.Cancel(); bool cancelled = false;
            try { UpdateEngine.Extract(archive, Path.Combine(root, "cancelled"), "0.1.5", cts.Token); } catch (OperationCanceledException) { cancelled = true; }
            Assert(cancelled, "Cancellation ignored");
            if (args.Length > 1 && args[1] == "--online") {
                var live = UpdateEngine.SelectRelease(UpdateEngine.DownloadText(new Uri(UpdateEngine.ReleasesUrl), CancellationToken.None), true);
                Assert(live != null && live.Version != null, "Official live release feed");
                Assert(UpdateEngine.AssetUri(live, live.Package).Host == "github.com", "Official live package URL");
                Console.WriteLine("Official GitHub release detected: " + live.tag_name);
                if (args.Length > 2 && args[2] == "--download") {
                    string sums = UpdateEngine.DownloadText(UpdateEngine.AssetUri(live, live.Checksums), CancellationToken.None);
                    string path = Path.Combine(root, "official-package.zip");
                    using (var stream = File.Create(path)) UpdateEngine.Download(UpdateEngine.AssetUri(live, live.Package), stream, live.Package.size, CancellationToken.None, null);
                    Assert(new FileInfo(path).Length == live.Package.size, "Live package size");
                    UpdateEngine.VerifyHash(path, UpdateEngine.ExpectedHash(sums, live.Package.name));
                    Console.WriteLine("Official package downloaded and SHA256 verified without executing it.");
                }
            }
            Console.WriteLine("OK: " + checks + " update checks (release selection, SHA256, safe archives, rollback, installed/portable data preservation, cancellation).");
        }
    }
}
