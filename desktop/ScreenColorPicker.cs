using System;
using System.ComponentModel;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace DeckEdgeDesktop
{
    // Surface de sélection presque transparente : aucune capture plein écran
    // n'est créée ou redessinée. Le pixel est lu après retrait de cette surface.
    internal sealed class ScreenColorPicker : Form
    {
        bool sampling, closing;
        Color? selectedColor;
        Exception samplingError;
        [DllImport("user32.dll")] static extern IntPtr GetDC(IntPtr window);
        [DllImport("user32.dll")] static extern int ReleaseDC(IntPtr window, IntPtr dc);
        [DllImport("gdi32.dll")] static extern uint GetPixel(IntPtr dc, int x, int y);
        [DllImport("dwmapi.dll")] static extern int DwmFlush();
        [DllImport("user32.dll")] static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);

        internal static Color? Pick(IWin32Window owner)
        {
            IntPtr previous = IntPtr.Zero;
            try {
                // Conserver les coordonnées physiques même avec plusieurs échelles Windows.
                previous = SetThreadDpiAwarenessContext(new IntPtr(-4));
                using (var picker = new ScreenColorPicker()) {
                    picker.ShowDialog(owner);
                    if (picker.samplingError != null) throw picker.samplingError;
                    return picker.selectedColor;
                }
            } finally {
                if (previous != IntPtr.Zero) SetThreadDpiAwarenessContext(previous);
            }
        }

        ScreenColorPicker()
        {
            Text = "DeckEdge — Pipette (Échap pour annuler)";
            FormBorderStyle = FormBorderStyle.None; StartPosition = FormStartPosition.Manual;
            AutoScaleMode = AutoScaleMode.None; BackColor = Color.Black;
            Opacity = 0.01; DoubleBuffered = true; Bounds = SystemInformation.VirtualScreen;
            TopMost = true; ShowInTaskbar = false; Cursor = Cursors.Cross; KeyPreview = true;
            KeyDown += delegate(object sender, KeyEventArgs e) {
                if (e.KeyCode == Keys.Escape) { DialogResult = DialogResult.Cancel; Close(); }
            };
            // Attendre le relâchement consomme le clic entier, sans l'envoyer dessous.
            MouseUp += async delegate(object sender, MouseEventArgs e) {
                if (sampling) return;
                if (e.Button == MouseButtons.Right) { DialogResult = DialogResult.Cancel; Close(); return; }
                if (e.Button != MouseButtons.Left) return;
                sampling = true;
                var point = Cursor.Position;
                Capture = true; Opacity = 0;
                try {
                    await Task.Delay(80);
                    if (closing || IsDisposed) return;
                    DwmFlush();
                    selectedColor = ReadPixel(point);
                    DialogResult = DialogResult.OK;
                } catch (Exception ex) { samplingError = ex; DialogResult = DialogResult.Cancel; }
                finally { if (!closing && !IsDisposed) { Capture = false; Close(); } }
            };
            FormClosing += delegate { closing = true; Capture = false; };
            Shown += delegate { Activate(); Focus(); };
        }

        internal static Color ReadPixel(Point point)
        {
            IntPtr dc = GetDC(IntPtr.Zero);
            if (dc == IntPtr.Zero) throw new Win32Exception();
            try {
                uint pixel = GetPixel(dc, point.X, point.Y);
                if (pixel == UInt32.MaxValue) throw new InvalidOperationException("Le pixel sélectionné n'est pas accessible.");
                return Color.FromArgb((int)(pixel & 255), (int)((pixel >> 8) & 255), (int)((pixel >> 16) & 255));
            } finally { ReleaseDC(IntPtr.Zero, dc); }
        }
    }
}
