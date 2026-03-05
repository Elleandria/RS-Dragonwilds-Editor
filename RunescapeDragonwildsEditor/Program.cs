using System;
using System.IO;
using System.Linq;
using System.Runtime.Versioning;
using Microsoft.Win32;

namespace DragonwildsUpdater
{
    [SupportedOSPlatform("windows")]
    internal class Program
    {
        // Expected Steam install path
        private const string DefaultSteamPath =
            @"C:\Program Files (x86)\Steam\steamapps\common\RSDragonwilds\RSDragonwilds\Content\Paks";

        // Config file sits next to updater.exe so path persists between runs
        private static readonly string ConfigPath =
            Path.Combine(AppContext.BaseDirectory, "updater_config.txt");

        static void Main(string[] args)
        {
            Console.Title = "Dragonwilds Save Editor — Updater";
            Console.WriteLine("============================================");
            Console.WriteLine("  Dragonwilds Save Editor — Data Updater");
            Console.WriteLine("  v0.10.2.2  |  github.com/Elleandria");
            Console.WriteLine("============================================");
            Console.WriteLine();

            // -- 1. Locate game Paks folder
            var paksDir = ResolvePaksDir();
            if (paksDir == null)
            {
                Console.WriteLine("ERROR: Could not locate game Paks folder.");
                Console.WriteLine("Please enter the full path to RSDragonwilds\\Content\\Paks:");
                paksDir = Console.ReadLine()?.Trim().Trim('"');
                if (string.IsNullOrEmpty(paksDir) || !Directory.Exists(paksDir))
                {
                    Console.WriteLine("Path not found. Exiting.");
                    Pause(); return;
                }
                // Save for next run
                File.WriteAllText(ConfigPath, paksDir);
                Console.WriteLine("Path saved. Won't ask again unless the folder moves.");
            }
            Console.WriteLine($"Game Paks: {paksDir}");

            // -- 2. Locate .usmap (newest in same folder as updater.exe)
            var usmapPath = ResolveUsmap();
            if (usmapPath == null)
            {
                Console.WriteLine("ERROR: No .usmap file found next to updater.exe.");
                Console.WriteLine("Place the UE4SS mapping file (*.usmap) in the same folder as DragonwildsUpdater.exe.");
                Pause(); return;
            }
            Console.WriteLine($"Mappings: {Path.GetFileName(usmapPath)}");

            // -- 3. Output dir = folder containing updater.exe
            //    (save_editor.exe and updater.exe live in the same folder)
            var outputDir = AppContext.BaseDirectory;
            Console.WriteLine($"Output:   {outputDir}");
            Console.WriteLine();

            // -- 4. Run extraction
            try
            {
                var extractor = new Extractor(paksDir, usmapPath, outputDir);
                extractor.Run();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\nFATAL ERROR: {ex.Message}");
                Console.WriteLine(ex.StackTrace);
                Pause();
            }
        }

        // ----------------------------------------------------------------
        // Locate Paks directory:
        //   1. Saved config file (user already pointed us here before)
        //   2. Default Steam path
        //   3. Steam registry key -> derive path
        // ----------------------------------------------------------------
        private static string? ResolvePaksDir()
        {
            // Check saved config first
            if (File.Exists(ConfigPath))
            {
                var saved = File.ReadAllText(ConfigPath).Trim();
                if (Directory.Exists(saved)) return saved;
            }

            // Try default Steam path
            if (Directory.Exists(DefaultSteamPath)) return DefaultSteamPath;

            // Try Steam registry to find alternate install location
            try
            {
                var steamPath = Registry.GetValue(
                    @"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Valve\Steam",
                    "InstallPath", null) as string
                    ?? Registry.GetValue(
                    @"HKEY_CURRENT_USER\SOFTWARE\Valve\Steam",
                    "SteamPath", null) as string;

                if (!string.IsNullOrEmpty(steamPath))
                {
                    var candidate = Path.Combine(
                        steamPath, "steamapps", "common",
                        "RSDragonwilds", "RSDragonwilds", "Content", "Paks");
                    if (Directory.Exists(candidate)) return candidate;

                    // Also scan steam library folders
                    var libraryFile = Path.Combine(steamPath, "steamapps", "libraryfolders.vdf");
                    if (File.Exists(libraryFile))
                    {
                        foreach (var line in File.ReadAllLines(libraryFile))
                        {
                            // VDF lines look like:   "path"   "D:\\SteamLibrary"
                            var match = System.Text.RegularExpressions.Regex.Match(
                                line, @"""path""\s+""([^""]+)""");
                            if (!match.Success) continue;
                            var libPath = match.Groups[1].Value.Replace(@"\\", @"\");
                            candidate = Path.Combine(
                                libPath, "steamapps", "common",
                                "RSDragonwilds", "RSDragonwilds", "Content", "Paks");
                            if (Directory.Exists(candidate)) return candidate;
                        }
                    }
                }
            }
            catch { /* registry not available on non-Windows, fall through */ }

            return null;
        }

        // ----------------------------------------------------------------
        // Find newest .usmap next to updater.exe
        // Picks by LastWriteTime so updating is: just drop a new .usmap in
        // ----------------------------------------------------------------
        private static string? ResolveUsmap()
        {
            var dir = AppContext.BaseDirectory;
            var usmaps = Directory.GetFiles(dir, "*.usmap", SearchOption.TopDirectoryOnly);
            if (usmaps.Length == 0) return null;
            return usmaps.OrderByDescending(f => File.GetLastWriteTime(f)).First();
        }

        private static void Pause()
        {
            Console.WriteLine("\nPress any key to exit.");
            Console.ReadKey();
        }
    }
}