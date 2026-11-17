using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;

namespace DeckEdgeDesktop
{
    internal sealed class ReleaseAsset
    {
        public string name { get; set; }
        public string browser_download_url { get; set; }
        public long size { get; set; }
    }
    internal sealed class AppRelease
    {
        public string tag_name { get; set; }
        public bool draft { get; set; }
        public bool prerelease { get; set; }
        public string body { get; set; }
        public ReleaseAsset[] assets { get; set; }
        internal Version Version { get { return UpdateEngine.ParseVersion(tag_name); } }
        internal ReleaseAsset Package { get { return (assets ?? new ReleaseAsset[0]).SingleOrDefault(a => a != null && a.name == "DeckEdge-" + tag_name.Substring(1) + "-Portable-x64.zip"); } }
        internal ReleaseAsset Checksums { get { return (assets ?? new ReleaseAsset[0]).SingleOrDefault(a => a != null && a.name == "SHA256SUMS.txt"); } }
    }
    internal sealed class UpdatePlan
    {
        public string Target { get; set; }
        public string Version { get; set; }
        public string Sha256 { get; set; }
        public bool Portable { get; set; }
        public int ProcessId { get; set; }
        public long ProcessStart { get; set; }
        public string Language { get; set; }
        public string DataDirectory { get; set; }
    }

    internal static class UpdateEngine
    {
        static UpdateEngine()
        {
            // The Framework compiler targets v4 by default. Opt out of its old
            // TLS compatibility switches without changing Windows/registry policy.
            AppContext.SetSwitch("Switch.System.Net.DontEnableSchUseStrongCrypto", false);
            AppContext.SetSwitch("Switch.System.Net.DontEnableSystemDefaultTlsVersions", false);
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
        }
        internal const string ReleasesUrl = "https://api.github.com/repos/Lorzo595/DeckEdge/releases?per_page=30";
        internal const long MaxPackage = 300L * 1024 * 1024;
        static readonly string[] PrivateNames = { "data", "media", ".phone-key", ".phones.json", ".device-id", "config.json", "config.json.bak", "app-settings.json", "discord_config.json", "config_safe_backup.json", ".desktop-profile", ".git", ".build" };
        internal static Version ParseVersion(string tag)
        {
            if (tag == null || !Regex.IsMatch(tag, @"^v\d+\.\d+\.\d+$")) return null;
            Version value;
            return System.Version.TryParse(tag.Substring(1) + ".0", out value) ? value : null;
        }
        internal static AppRelease SelectRelease(string json, bool includePrereleases)
        {
            var releases = new JavaScriptSerializer { MaxJsonLength = 2 * 1024 * 1024 }.Deserialize<AppRelease[]>(json);
            return (releases ?? new AppRelease[0]).Where(r => r != null && !r.draft && (includePrereleases || !r.prerelease) && r.Version != null)
                .Where(r => r.assets != null && r.assets.Count(a => a != null && a.name == "DeckEdge-" + r.tag_name.Substring(1) + "-Portable-x64.zip") == 1
                    && r.assets.Count(a => a != null && a.name == "SHA256SUMS.txt") == 1)
                .OrderByDescending(r => r.Version).FirstOrDefault();
        }
        internal static Uri AssetUri(AppRelease release, ReleaseAsset asset)
        {
            string expected = "https://github.com/Lorzo595/DeckEdge/releases/download/" + release.tag_name + "/" + asset.name;
            if (asset.browser_download_url != expected || asset.size <= 0 || asset.size > MaxPackage)
                throw new InvalidDataException("Invalid official release asset.");
            return new Uri(expected);
        }
        static void CheckHost(Uri uri)
        {
            if (uri.Scheme != "https" || !uri.IsDefaultPort || !String.IsNullOrEmpty(uri.UserInfo)
                || !new[] { "api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com" }.Contains(uri.Host.ToLowerInvariant()))
                throw new InvalidDataException("Unexpected update download destination.");
        }
        internal static void Download(Uri uri, Stream output, long limit, CancellationToken token, Action<long> progress)
        {
            for (int redirect = 0; redirect < 6; redirect++) {
                token.ThrowIfCancellationRequested(); CheckHost(uri);
                var request = (HttpWebRequest)WebRequest.Create(uri);
                request.UserAgent = "DeckEdge-Updater"; request.Accept = "application/vnd.github+json";
                request.Timeout = 15000; request.ReadWriteTimeout = 30000; request.AllowAutoRedirect = false;
                using (token.Register(request.Abort))
                using (var response = (HttpWebResponse)request.GetResponse()) {
                    if ((int)response.StatusCode >= 300 && (int)response.StatusCode < 400) {
                        uri = new Uri(uri, response.Headers["Location"]); continue;
                    }
                    if (response.StatusCode != HttpStatusCode.OK || response.ContentLength > limit) throw new InvalidDataException("Invalid update response size.");
                    using (var input = response.GetResponseStream()) {
                        var buffer = new byte[65536]; long total = 0; int read;
                        while ((read = input.Read(buffer, 0, buffer.Length)) > 0) {
                            token.ThrowIfCancellationRequested(); total += read;
                            if (total > limit) throw new InvalidDataException("Update download exceeds its size limit.");
                            output.Write(buffer, 0, read); if (progress != null) progress(total);
                        }
                    }
                    return;
                }
            }
            throw new InvalidDataException("Too many update redirects.");
        }
        internal static string DownloadText(Uri uri, CancellationToken token)
        {
            using (var stream = new MemoryStream()) { Download(uri, stream, 2 * 1024 * 1024, token, null); return Encoding.UTF8.GetString(stream.ToArray()); }
        }
        internal static string ExpectedHash(string sums, string name)
        {
            var matches = Regex.Matches(sums, @"(?m)^([a-fA-F0-9]{64})[ \t]+\*?" + Regex.Escape(name) + @"\r?$");
            if (matches.Count != 1) throw new InvalidDataException("Missing or ambiguous update checksum.");
            return matches[0].Groups[1].Value.ToLowerInvariant();
        }
        internal static void VerifyHash(string file, string expected)
        {
            if (expected == null || !Regex.IsMatch(expected, "^[a-f0-9]{64}$")) throw new InvalidDataException("Invalid SHA256.");
            using (var stream = File.OpenRead(file)) using (var hash = SHA256.Create())
                if (BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant() != expected)
                    throw new InvalidDataException("Update checksum mismatch.");
        }
        internal static string SafeRelative(string name)
        {
            string relative = name.Replace('\\', '/');
            if (!relative.StartsWith("DeckEdge/", StringComparison.Ordinal) || relative.Length <= 9) throw new InvalidDataException("Invalid package root.");
            relative = relative.Substring(9);
            var parts = relative.Split('/');
            if (parts.Any(p => String.IsNullOrEmpty(p) || p == "." || p == ".." || p.EndsWith(".") || p.EndsWith(" ") || p.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
                || PrivateNames.Contains(parts[0], StringComparer.OrdinalIgnoreCase)) throw new InvalidDataException("Unsafe update path: " + name);
            return relative.Replace('/', Path.DirectorySeparatorChar);
        }
        internal static void AssertNoLinks(string path)
        {
            var info = new DirectoryInfo(Path.GetFullPath(path));
            while (info != null) {
                if (info.Exists && (info.Attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("Update paths cannot use filesystem links.");
                info = info.Parent;
            }
            if (File.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new IOException("Update file is a filesystem link.");
        }
        internal static void Extract(string archive, string destination, string version, CancellationToken token)
        {
            Directory.CreateDirectory(destination); AssertNoLinks(destination);
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase); long total = 0;
            using (var zip = ZipFile.OpenRead(archive)) {
                if (zip.Entries.Count > 30000) throw new InvalidDataException("Too many package entries.");
                foreach (var entry in zip.Entries) {
                    token.ThrowIfCancellationRequested();
                    if (entry.FullName.EndsWith("/") || entry.FullName.EndsWith("\\")) { if (entry.Length != 0) throw new InvalidDataException("Invalid directory entry."); continue; }
                    string relative = SafeRelative(entry.FullName);
                    if (!seen.Add(relative)) throw new InvalidDataException("Duplicate package file.");
                    total += entry.Length;
                    if (entry.Length < 0 || total > 1024L * 1024 * 1024) throw new InvalidDataException("Unpacked update exceeds its size limit.");
                    string target = Path.Combine(destination, relative); Directory.CreateDirectory(Path.GetDirectoryName(target));
                    using (var input = entry.Open()) using (var output = new FileStream(target, FileMode.CreateNew)) {
                        var buffer = new byte[65536]; long copied = 0; int read;
                        while ((read = input.Read(buffer, 0, buffer.Length)) > 0) {
                            token.ThrowIfCancellationRequested(); copied += read;
                            if (copied > entry.Length) throw new InvalidDataException("Invalid expanded file size.");
                            output.Write(buffer, 0, read);
                        }
                        if (copied != entry.Length) throw new InvalidDataException("Incomplete expanded file.");
                    }
                }
            }
            foreach (string required in new[] { "DeckEdge.exe", "VERSION", "desktop_backend.py", "portable.flag", "runtime/python.exe" })
                if (!File.Exists(Path.Combine(destination, required))) throw new InvalidDataException("Incomplete update package: " + required);
            if (ParseVersion("v" + File.ReadAllText(Path.Combine(destination, "VERSION")).Trim()) != ParseVersion("v" + version))
                throw new InvalidDataException("Package version does not match the release.");
        }
        internal static void ValidateTarget(UpdatePlan plan)
        {
            if (ParseVersion("v" + plan.Version) == null || String.IsNullOrEmpty(plan.Target) || !Path.IsPathRooted(plan.Target)) throw new InvalidDataException("Invalid update plan.");
            AssertNoLinks(plan.Target);
            if (!File.Exists(Path.Combine(plan.Target, "DeckEdge.exe")) || !File.Exists(Path.Combine(plan.Target, "desktop_backend.py")) || !File.Exists(Path.Combine(plan.Target, "VERSION"))
                || File.Exists(Path.Combine(plan.Target, "portable.flag")) != plan.Portable) throw new InvalidDataException("The update target is not this DeckEdge installation.");
            Version installed = ParseVersion("v" + File.ReadAllText(Path.Combine(plan.Target, "VERSION")).Trim());
            if (installed == null || ParseVersion("v" + plan.Version) <= installed) throw new InvalidDataException("The update is already installed or older than this copy.");
        }
        internal static string InstanceKey(string target)
        {
            // Same canonical spelling as Program.Project for packaged editions.
            string path = Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            using (var hash = SHA256.Create()) return "Local\\DeckEdge-" + BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(path.ToLowerInvariant()))).Replace("-", "").Substring(0, 20);
        }
        // Back up every replaced file before the first write. Never touch user data,
        // unknown files or portable.flag (the same payload updates both editions).
        internal static void Apply(UpdatePlan plan, string payload, string backup, Action<int> afterWrite)
        {
            ValidateTarget(plan); AssertNoLinks(payload); AssertNoLinks(backup);
            if (Directory.Exists(backup)) throw new IOException("Update backup already exists.");
            var files = Directory.GetFiles(payload, "*", SearchOption.AllDirectories)
                .Select(f => SafeRelative("DeckEdge/" + f.Substring(payload.TrimEnd(Path.DirectorySeparatorChar).Length + 1).Replace('\\', '/')))
                .Where(f => !String.Equals(f, "portable.flag", StringComparison.OrdinalIgnoreCase)).ToArray();
            var replaced = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var written = new List<string>();
            Directory.CreateDirectory(backup);
            foreach (string file in files) {
                string target = Path.Combine(plan.Target, file); AssertNoLinks(target);
                if (!String.IsNullOrEmpty(plan.DataDirectory)) {
                    string data = Path.GetFullPath(plan.DataDirectory).TrimEnd(Path.DirectorySeparatorChar);
                    if (!String.Equals(data, Path.GetFullPath(plan.Target).TrimEnd(Path.DirectorySeparatorChar), StringComparison.OrdinalIgnoreCase)
                        && (target.StartsWith(data + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) || String.Equals(target, data, StringComparison.OrdinalIgnoreCase)))
                        throw new InvalidDataException("Update payload overlaps the custom data directory.");
                }
                if (File.Exists(target)) {
                    string saved = Path.Combine(backup, file); Directory.CreateDirectory(Path.GetDirectoryName(saved)); File.Copy(target, saved);
                    replaced.Add(file);
                }
            }
            try {
                foreach (string file in files) {
                    string target = Path.Combine(plan.Target, file); AssertNoLinks(target);
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    written.Add(file); File.Copy(Path.Combine(payload, file), target, true);
                    if (afterWrite != null) afterWrite(written.Count);
                }
            } catch (Exception error) {
                var failures = new List<Exception>();
                foreach (string file in written.AsEnumerable().Reverse()) try {
                    string target = Path.Combine(plan.Target, file);
                    if (replaced.Contains(file)) File.Copy(Path.Combine(backup, file), target, true);
                    else if (File.Exists(target)) File.Delete(target);
                } catch (Exception rollback) { failures.Add(rollback); }
                if (failures.Count > 0) { failures.Insert(0, error); throw new AggregateException("Restore the update backup at " + backup, failures); }
                throw;
            }
        }
    }
}
