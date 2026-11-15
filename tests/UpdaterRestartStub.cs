using System;
using System.IO;
using System.Threading;
internal static class UpdaterRestartStub
{
    static void Main(string[] args)
    {
        if (args.Length > 0 && args[0] == "--wait") { Thread.Sleep(5000); return; }
        File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "restart.marker"), Environment.GetEnvironmentVariable("DECKEDGE_DATA_DIR") ?? "missing data directory");
    }
}
