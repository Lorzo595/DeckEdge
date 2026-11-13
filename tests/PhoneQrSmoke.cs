using System;
using System.Drawing;
using System.Drawing.Imaging;

namespace DeckEdgeDesktop
{
    internal static class Program
    {
        internal static string PhoneKey = new String('a', 64);
        internal static string PhoneHost = "deckedge-000000000001.local";
        internal static bool PhoneDiscoveryReady = true;

        [STAThread]
        static void Main(string[] args)
        {
            string url = "http://" + PhoneHost + ":5000/?key=" + PhoneKey;
            using (Bitmap image = PhoneConnection.QrImage(url)) {
                if (image.Width != image.Height || image.Width > 320) throw new Exception("Dimensions du QR incorrectes.");
                if (image.GetPixel(0, 0).ToArgb() != Color.White.ToArgb()) throw new Exception("Marge blanche manquante.");
                image.Save(args[0], ImageFormat.Png);
            }
            var addresses = PhoneConnection.Addresses(PhoneKey);
            if (addresses.Length > 0 && !addresses[0].Url.StartsWith("http://" + PhoneHost)) throw new Exception("Adresse permanente non prioritaire.");
            Console.WriteLine("OK : image QR avec marge blanche et adresse permanente prioritaire. Données simulées.");
        }
    }
}
