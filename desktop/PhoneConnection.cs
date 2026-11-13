using System;
using System.Drawing;
using System.Linq;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Threading.Tasks;
using System.Windows.Forms;
using QRCoder;

namespace DeckEdgeDesktop
{
    internal sealed class PhoneAddress
    {
        internal string Name, Url;
        public override string ToString() { return Name; }
    }

    internal static class PhoneConnection
    {
        internal static PhoneAddress[] Addresses(string key, bool includePermanent = true)
        {
            var addresses = NetworkInterface.GetAllNetworkInterfaces()
                .Where(n => n.OperationalStatus == OperationalStatus.Up && n.NetworkInterfaceType != NetworkInterfaceType.Loopback && n.NetworkInterfaceType != NetworkInterfaceType.Tunnel)
                .OrderByDescending(n => n.GetIPProperties().GatewayAddresses.Any(g => g.Address.AddressFamily == AddressFamily.InterNetwork && !g.Address.Equals(IPAddress.Any)))
                .ThenBy(n => n.NetworkInterfaceType == NetworkInterfaceType.Wireless80211 ? 0 : n.NetworkInterfaceType == NetworkInterfaceType.Ethernet ? 1 : 2)
                .SelectMany(n => n.GetIPProperties().UnicastAddresses
                    .Where(a => a.Address.AddressFamily == AddressFamily.InterNetwork && !IPAddress.IsLoopback(a.Address) && !a.Address.ToString().StartsWith("169.254.") && !a.Address.Equals(IPAddress.Any))
                    .Select(a => new PhoneAddress { Name = n.Name + " · " + a.Address, Url = "http://" + a.Address + ":5000/?key=" + key }))
                .GroupBy(a => a.Url).Select(g => g.First()).ToArray();
            if (includePermanent && addresses.Length > 0 && Program.PhoneDiscoveryReady && !String.IsNullOrEmpty(Program.PhoneHost))
                return new[] { new PhoneAddress { Name = "Ce PC · adresse permanente (recommandée)", Url = "http://" + Program.PhoneHost + ":5000/?key=" + key } }.Concat(addresses).ToArray();
            return addresses;
        }

        internal static Bitmap QrImage(string url)
        {
            using (var generator = new QRCodeGenerator())
            using (var data = generator.CreateQrCode(url, QRCodeGenerator.ECCLevel.Q))
            using (var code = new QRCode(data))
                return code.GetGraphic(Math.Max(3, 300 / data.ModuleMatrix.Count), Color.Black, Color.White, true);
        }
    }

    internal sealed class PhoneConnectionForm : Form
    {
        readonly ComboBox network = new ComboBox();
        readonly PictureBox qr = new PictureBox();
        readonly Label connection = new Label();
        readonly TextBox manual = new TextBox();
        readonly Button copy = new Button();
        readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
        readonly Func<Task<int>> clientCount;
        bool polling;
        bool permanentShown, selectedByUser;

        internal PhoneConnectionForm(Func<Task<int>> readClientCount)
        {
            clientCount = readClientCount;
            Text = "Connecter votre téléphone"; ClientSize = new Size(540, Math.Min(710, Screen.PrimaryScreen.WorkingArea.Height - 90));
            FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false; MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent; ShowInTaskbar = false;
            BackColor = Color.FromArgb(33, 35, 42); ForeColor = Color.FromArgb(235, 239, 248);
            Font = new Font("Segoe UI", 10); AutoScaleMode = AutoScaleMode.Dpi;
            var content = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, Padding = new Padding(24, 18, 24, 18), AutoScroll = true };
            Controls.Add(content);
            AddText(content, "Votre Deck, à portée de main.", 19, Color.White, 10);
            AddText(content, "Sur votre téléphone, ouvrez l’appareil photo et scannez le QR code. Le PC et le téléphone doivent être sur le même réseau privé.", 10, ForeColor, 14);
            network.DropDownStyle = ComboBoxStyle.DropDownList; network.Width = 470; network.Margin = new Padding(0, 0, 0, 12);
            network.AccessibleName = "Réseau utilisé pour connecter le téléphone";
            network.SelectedIndexChanged += delegate { UpdateQr(); };
            network.SelectionChangeCommitted += delegate { selectedByUser = true; };
            content.Controls.Add(network);
            var card = new Panel { Width = 470, Height = 320, BackColor = Color.White, Margin = new Padding(0, 0, 0, 12) };
            qr.Dock = DockStyle.Fill; qr.SizeMode = PictureBoxSizeMode.CenterImage;
            qr.AccessibleName = "QR code privé de connexion au pupitre"; card.Controls.Add(qr); content.Controls.Add(card);
            connection.AutoSize = true; connection.MaximumSize = new Size(470, 0); connection.Margin = new Padding(0, 0, 0, 10); connection.Text = "En attente du téléphone…";
            content.Controls.Add(connection);
            var buttons = new FlowLayoutPanel { Width = 470, Height = 40, Margin = new Padding(0, 0, 0, 6) };
            copy.Text = "Copier le lien"; copy.AutoSize = true; copy.FlatStyle = FlatStyle.Flat;
            copy.Click += delegate { var address = network.SelectedItem as PhoneAddress; if (address != null) { try { Clipboard.SetText(address.Url); copy.Text = "Lien copié"; } catch { connection.Text = "Copie indisponible. Vous pouvez afficher le lien manuel."; } } };
            var refresh = new Button { Text = "Actualiser les réseaux", AutoSize = true, FlatStyle = FlatStyle.Flat };
            refresh.Click += delegate { RefreshAddresses(); };
            buttons.Controls.Add(copy); buttons.Controls.Add(refresh); content.Controls.Add(buttons);
            var showManual = new CheckBox { Text = "Afficher le lien manuel", AutoSize = true, Margin = new Padding(0, 2, 0, 7) };
            manual.ReadOnly = true; manual.Width = 470; manual.Visible = false; manual.AccessibleName = "Lien privé complet du téléphone";
            showManual.CheckedChanged += delegate { manual.Visible = showManual.Checked; };
            content.Controls.Add(showManual); content.Controls.Add(manual);
            AddText(content, "Une seule association suffit : ajoutez ensuite DeckEdge à l’écran d’accueil du téléphone. La clé de ce PC reste conservée aux prochains démarrages.", 9, Color.FromArgb(163, 175, 199), 8);
            AddText(content, "Ce QR code et son lien donnent accès à votre pupitre : gardez-les privés. Le code est généré localement, sans service externe.", 9, Color.FromArgb(163, 175, 199), 8);
            AddText(content, "Si la connexion échoue : vérifiez le même réseau Wi-Fi/Ethernet, évitez le Wi-Fi invité et choisissez une autre adresse ci-dessus si un VPN est actif. Le pare-feu doit autoriser DeckEdge sur le réseau privé.", 9, Color.FromArgb(163, 175, 199), 8);
            var footer = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 60, Padding = new Padding(24, 8, 0, 8), BackColor = BackColor };
            var close = new Button { Text = "Fermer", AutoSize = true, FlatStyle = FlatStyle.Flat, DialogResult = DialogResult.Cancel };
            footer.Controls.Add(close); Controls.Add(footer); CancelButton = close;
            timer.Interval = 1500; timer.Tick += async delegate { await RefreshStatus(); };
            Shown += async delegate { RefreshAddresses(); timer.Start(); await RefreshStatus(); };
            FormClosed += delegate { timer.Stop(); timer.Dispose(); if (qr.Image != null) { var image = qr.Image; qr.Image = null; image.Dispose(); } };
        }

        static void AddText(FlowLayoutPanel panel, string text, int size, Color color, int margin)
        {
            panel.Controls.Add(new Label { Text = text, AutoSize = true, MaximumSize = new Size(470, 0), Font = new Font("Segoe UI", size), ForeColor = color, Margin = new Padding(0, 0, 0, margin) });
        }

        void RefreshAddresses()
        {
            string previous = (network.SelectedItem as PhoneAddress) == null ? null : ((PhoneAddress)network.SelectedItem).Url;
            try {
                var addresses = PhoneConnection.Addresses(Program.PhoneKey);
                permanentShown = Program.PhoneDiscoveryReady && !String.IsNullOrEmpty(Program.PhoneHost);
                network.Items.Clear(); network.Items.AddRange(addresses);
                network.Enabled = addresses.Length > 0;
                if (addresses.Length > 0) { int selected = selectedByUser ? Array.FindIndex(addresses, a => a.Url == previous) : 0; network.SelectedIndex = Math.Max(0, selected); }
                else { UpdateQr(); connection.Text = "Aucun réseau local détecté. Connectez le PC au Wi-Fi ou à Ethernet, puis actualisez."; }
            } catch { UpdateQr(); connection.Text = "Réseaux indisponibles. Vérifiez la connexion du PC et actualisez."; }
        }

        void UpdateQr()
        {
            var address = network.SelectedItem as PhoneAddress;
            var old = qr.Image; qr.Image = null; if (old != null) old.Dispose();
            manual.Text = address == null ? "" : address.Url; copy.Enabled = address != null; copy.Text = "Copier le lien";
            if (address != null) {
                try { qr.Image = PhoneConnection.QrImage(address.Url); }
                catch { connection.Text = "QR code indisponible. Utilisez le lien manuel."; }
            }
        }

        async Task RefreshStatus()
        {
            if (polling || IsDisposed || Disposing) return;
            polling = true;
            try {
                int count = await clientCount();
                if (IsDisposed || Disposing) return;
                if (permanentShown != Program.PhoneDiscoveryReady) RefreshAddresses();
                connection.ForeColor = count > 0 ? Color.FromArgb(112, 218, 158) : Color.FromArgb(180, 195, 222);
                if (network.Items.Count == 0) return;
                connection.Text = count > 0 ? "Pupitre connecté · vous pouvez utiliser DeckEdge sur votre téléphone." : count < 0 ? "Le serveur ne répond pas encore. Gardez DeckEdge ouvert." : "Serveur prêt · scannez le QR code pour connecter le téléphone.";
            } catch { if (!IsDisposed && !Disposing) connection.Text = "Vérification du serveur indisponible."; }
            finally { polling = false; }
        }
    }
}
