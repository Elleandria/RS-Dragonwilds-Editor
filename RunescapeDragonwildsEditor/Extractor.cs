using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Texture;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Assets.Objects.Properties;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse.UE4.Versions;
using CUE4Parse_Conversion.Textures;
using SkiaSharp;

namespace DragonwildsUpdater
{
    public class ItemEntry
    {
        [JsonPropertyName("SourceString")]
        public string SourceString { get; set; } = "";

        [JsonPropertyName("PersistenceID")]
        public string PersistenceID { get; set; } = "";

        [JsonPropertyName("Weight")]
        public float Weight { get; set; } = 0f;

        [JsonPropertyName("MaxStackSize")]
        public int MaxStackSize { get; set; } = 1;

        [JsonPropertyName("VitalShield")]
        public int VitalShield { get; set; } = 0;

        [JsonPropertyName("IconFile")]
        public string IconFile { get; set; } = "ICON PLACEHOLDER.png";

        [JsonPropertyName("Category")]
        public string Category { get; set; } = "Basic Item";

        [JsonPropertyName("PowerLevel")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public int? PowerLevel { get; set; }

        [JsonPropertyName("BaseDurability")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public int? BaseDurability { get; set; }
    }

    public class Extractor
    {
        private readonly string _paksDir;
        private readonly string _usmapPath;
        private readonly string _outputItemJson;
        private readonly string _outputIconsDir;
        private readonly string _outputIconsOldDir;
        private readonly string _outputDiscoveryLog;

        private static readonly string[] BuildingKeywords =
        {
            "_building_", "_build_", "_furniture_", "_wall_", "_floor_",
            "_roof_", "_foundation_", "_stair_", "_door_", "_window_",
            "_fence_", "_gate_", "_pillar_", "_beam_", "_base_building_"
        };

        // Paths that contain ITEM_ files but are not actual inventory items.
        // Add to this list if a new patch introduces false-positive folders.
        private static readonly string[] ExcludedPathSegments =
        {
            "/Art/",
            "/VFX/",
            "/FX/",
            "/Meshes/",
            "/Animations/",
            "/Blueprints/NPC",
            "/AI/",
        };

        public Extractor(string paksDir, string usmapPath, string outputDir)
        {
            _paksDir            = paksDir;
            _usmapPath          = usmapPath;
            _outputItemJson     = Path.Combine(outputDir, "data", "ItemID.json");
            _outputIconsDir     = Path.Combine(outputDir, "assets", "UI");
            _outputIconsOldDir  = Path.Combine(outputDir, "assets", "UI", "old");
            _outputDiscoveryLog = Path.Combine(outputDir, "ItemFolderDiscovery.txt");
        }

        public void Run()
        {
            Console.WriteLine("=== Dragonwilds Updater ===");
            Console.WriteLine($"Paks:   {_paksDir}");
            Console.WriteLine($"Usmap:  {_usmapPath}");
            Console.WriteLine();

            Console.WriteLine("[1/4] Opening game files...");
            #pragma warning disable CS0618
            var provider = new DefaultFileProvider(
                _paksDir,
                SearchOption.TopDirectoryOnly,
                true,
                new VersionContainer(EGame.GAME_UE5_6)
            );
            #pragma warning restore CS0618

            provider.MappingsContainer = new FileUsmapTypeMappingsProvider(_usmapPath);
            provider.Initialize();
            provider.Mount();
            Console.WriteLine($"      Mounted {provider.Files.Count} files.");

            // --- Discovery: find and log all folders that contain ITEM_ assets ---
            WriteDiscoveryLog(provider);

            Console.WriteLine("\n[2/4] Extracting item data...");
            var items = ExtractItems(provider);
            WriteItemJson(items);
            Console.WriteLine($"      Wrote {items.Count} items to ItemID.json");

            Console.WriteLine("\n[3/4] Extracting icons...");
            var referencedIcons = items
                .Select(i => i.IconFile)
                .ToHashSet(StringComparer.OrdinalIgnoreCase);
            ExtractIcons(provider, referencedIcons);

            Console.WriteLine("\n[4/4] Deprecating unused icons...");
            DeprecateUnusedIcons(referencedIcons);

            Console.WriteLine("\nDone!");
        }

        // -------------------------------------------------------------------------
        // Discovery: writes ItemFolderDiscovery.txt listing every unique folder
        // that contains at least one ITEM_*.uasset, sorted alphabetically.
        // Use this after a patch to spot new areas where Jagex added items.
        // -------------------------------------------------------------------------
        private void WriteDiscoveryLog(DefaultFileProvider provider)
        {
            var folders = provider.Files.Keys
                .Where(p =>
                    Path.GetFileName(p).StartsWith("ITEM_", StringComparison.OrdinalIgnoreCase) &&
                    p.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase))
                .Select(p =>
                {
                    // Normalise to forward slashes and strip the filename
                    var norm = p.Replace('\\', '/');
                    var lastSlash = norm.LastIndexOf('/');
                    return lastSlash >= 0 ? norm[..lastSlash] : norm;
                })
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(f => f, StringComparer.OrdinalIgnoreCase)
                .ToList();

            Directory.CreateDirectory(Path.GetDirectoryName(_outputDiscoveryLog)!);

            var lines = new List<string>
            {
                $"# ItemFolderDiscovery — generated {DateTime.UtcNow:yyyy-MM-dd HH:mm} UTC",
                $"# {folders.Count} unique folders contain ITEM_*.uasset files.",
                $"# Use this to spot new folders added in game patches.",
                ""
            };
            lines.AddRange(folders);

            File.WriteAllLines(_outputDiscoveryLog, lines, Encoding.UTF8);
            Console.WriteLine($"      Discovery log: {folders.Count} ITEM_ folders → ItemFolderDiscovery.txt");
        }

        // -------------------------------------------------------------------------
        // Item extraction: searches the ENTIRE pak for ITEM_*.uasset, not just
        // /Content/Gameplay/. This catches shop items, economy items, or any new
        // area Jagex adds in a patch. Non-inventory paths are filtered out by
        // ExcludedPathSegments above.
        // -------------------------------------------------------------------------
        private List<ItemEntry> ExtractItems(DefaultFileProvider provider)
        {
            var items = new List<ItemEntry>();
            var seen  = new HashSet<string>();

            var itemPaths = provider.Files.Keys
                .Where(p =>
                    Path.GetFileName(p).StartsWith("ITEM_", StringComparison.OrdinalIgnoreCase) &&
                    p.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase) &&
                    !ExcludedPathSegments.Any(seg =>
                        p.Contains(seg, StringComparison.OrdinalIgnoreCase)) &&
                    !BuildingKeywords.Any(kw =>                                    // ← ADD THIS
                        Path.GetFileName(p).Contains(kw, StringComparison.OrdinalIgnoreCase)))
                .ToList();

            Console.WriteLine($"      Found {itemPaths.Count} ITEM_ assets (all pak paths).");

            foreach (var path in itemPaths)
            {
                try
                {
                    var package = provider.LoadPackage(path);
                    if (package == null) continue;

                    foreach (var exportLazy in package.ExportsLazy)
                    {
                        var export = exportLazy.Value;
                        if (export is not UObject uobj) continue;

                        var entry = ParseItemExport(uobj);
                        if (entry == null) continue;
                        if (seen.Contains(entry.PersistenceID)) continue;
                        seen.Add(entry.PersistenceID);
                        items.Add(entry);
                        Console.WriteLine($"      + {entry.SourceString} [{entry.PersistenceID}]");
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"      Skip {Path.GetFileName(path)}: {ex.Message}");
                }
            }

            // --- Vestige items (DA_Consumable_Vestige_*.uasset) ---
            var vestigePaths = provider.Files.Keys
                .Where(p =>
                    p.Contains("/Consumables/Vestiges/", StringComparison.OrdinalIgnoreCase) &&
                    Path.GetFileName(p).StartsWith("DA_Consumable_Vestige_", StringComparison.OrdinalIgnoreCase) &&
                    p.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase))
                .ToList();

            Console.WriteLine($"      Found {vestigePaths.Count} Vestige DA_ assets.");

            items.Sort((a, b) =>
                string.Compare(a.SourceString, b.SourceString, StringComparison.OrdinalIgnoreCase));
            return items;
        }

        private ItemEntry? ParseItemExport(UObject export)
        {
            string? sourceName     = null;
            string? pid            = null;
            float   weight         = 0f;
            int     maxStack       = 1;
            int     vitalShield    = 0;
            string  iconFile       = "ICON PLACEHOLDER.png";
            int?    powerLevel     = null;
            int?    baseDurability = null;

            foreach (var prop in export.Properties)
            {
                switch (prop.Name.Text)
                {
                    case "Name":
                    case "DisplayName":
                        sourceName = ReadFText(prop.Tag);
                        break;

                    case "PersistenceID":
                    case "ItemID":
                    case "PersistentID":
                        pid = prop.Tag?.GenericValue?.ToString();
                        break;

                    case "Weight":
                        weight = ReadFloat(prop.Tag);
                        break;

                    case "MaxStackSize":
                        maxStack = ReadInt(prop.Tag, 1);
                        break;

                    case "VitalShield":
                        vitalShield = ReadInt(prop.Tag, 0);
                        break;

                    case "PowerLevel":
                        var pl = ReadInt(prop.Tag, -1);
                        if (pl >= 0) powerLevel = pl;
                        break;

                    case "BaseDurability":
                        var bd = ReadInt(prop.Tag, 0);
                        if (bd > 0) baseDurability = bd;
                        break;

                    case "Icon":
                        iconFile = ExtractIconFilename(prop.Tag);
                        break;
                }
            }

            if (string.IsNullOrWhiteSpace(sourceName) || string.IsNullOrWhiteSpace(pid))
                return null;

            return new ItemEntry
            {
                SourceString   = sourceName.Trim(),
                PersistenceID  = pid,
                Weight         = weight,
                MaxStackSize   = maxStack,
                VitalShield    = vitalShield,
                IconFile       = iconFile,
                Category       = GetCategory(sourceName),
                PowerLevel     = powerLevel,
                BaseDurability = baseDurability
            };
        }

        private static string? ReadFText(FPropertyTagType? tag)
        {
            if (tag == null) return null;
            if (tag.GenericValue is FText ft)
                return string.IsNullOrWhiteSpace(ft.Text) ? null : ft.Text;
            var raw = tag.ToString() ?? "";
            return string.IsNullOrWhiteSpace(raw) || raw == "None" ? null : raw;
        }

        private static float ReadFloat(FPropertyTagType? tag)
        {
            if (tag?.GenericValue is float f)  return f;
            if (tag?.GenericValue is double d) return (float)d;
            if (float.TryParse(tag?.GenericValue?.ToString(), out var p)) return p;
            return 0f;
        }

        private static int ReadInt(FPropertyTagType? tag, int defaultVal)
        {
            if (tag?.GenericValue is int i)  return i;
            if (tag?.GenericValue is long l) return (int)l;
            if (int.TryParse(tag?.GenericValue?.ToString(), out var p)) return p;
            return defaultVal;
        }

        private static string ExtractIconFilename(FPropertyTagType? tag)
        {
            if (tag == null) return "ICON PLACEHOLDER.png";

            string raw;
            if (tag.GenericValue is FSoftObjectPath sop)
                raw = sop.AssetPathName.Text;
            else
                raw = tag.GenericValue?.ToString() ?? tag.ToString() ?? "";

            if (string.IsNullOrWhiteSpace(raw) || raw == "None")
                return "ICON PLACEHOLDER.png";

            // /Game/Art/UI/Icons/T_Icon_Name.T_Icon_Name -> T_Icon_Name
            var dotIdx = raw.LastIndexOf('.');
            if (dotIdx > 0)
                raw = raw[(dotIdx + 1)..];
            else
            {
                var slashIdx = raw.LastIndexOf('/');
                if (slashIdx >= 0) raw = raw[(slashIdx + 1)..];
            }

            raw = raw.Trim('\'').Trim();
            return string.IsNullOrWhiteSpace(raw) || raw == "None"
                ? "ICON PLACEHOLDER.png"
                : raw + ".png";
        }

        private static string GetCategory(string name)
        {
            var categories = new (string Key, string Cat)[]
            {
                ("Sword",      "Melee Weapons"),
                ("Scimitar",   "Melee Weapons"),
                ("Dagger",     "Melee Weapons"),
                ("Knife",      "Melee Weapons"),
                ("Battleaxe",  "Melee Weapons"),
                ("Warhammer",  "Melee Weapons"),
                ("Maul",       "Melee Weapons"),
                ("Club",       "Melee Weapons"),
                ("Whip",       "Melee Weapons"),
                ("Spear",      "Polearms"),
                ("Halberd",    "Polearms"),
                ("Staff",      "Staves"),
                ("Crossbow",   "Crossbows"),
                ("Bow",        "Bows"),
                ("Shield",     "Shields"),
                ("Kite",       "Shields"),
                ("Buckler",    "Shields"),
                ("Defender",   "Shields"),
                ("Platebody",  "Chestplates"),
                ("Body",       "Chestplates"),
                ("Robe",       "Chestplates"),
                ("Tunic",      "Chestplates"),
                ("Platelegs",  "Leggings"),
                ("Legs",       "Leggings"),
                ("Chaps",      "Leggings"),
                ("Helm",       "Helms"),
                ("Cowl",       "Helms"),
                ("Hat",        "Helms"),
                ("Hood",       "Helms"),
                ("Scarf",      "Helms"),
                ("Boots",      "Boots"),
                ("Gloves",     "Gloves"),
                ("Ring",       "Rings"),
                ("Amulet",     "Amulets"),
                ("Necklace",   "Amulets"),
                ("Pendant",    "Amulets"),
                ("Arrow",      "Arrows"),
                ("Bolt",       "Arrows"),
                ("Dart",       "Arrows"),
                ("Pickaxe",    "Tools"),
                ("Hatchet",    "Tools"),
                ("Axe",        "Tools"),
                ("Ore",        "Ores"),
                ("Bar",        "Bars"),
                ("Logs",       "Woodcutting"),
                ("Plank",      "Woodcutting"),
                ("Wood",       "Woodcutting"),
                ("Rune",       "Runes"),
                ("Essence",    "Runecrafting"),
                ("Seeds",      "Farming"),
                ("Seed",       "Farming"),
                ("Pie",        "Food"),
                ("Stew",       "Food"),
                ("Soup",       "Food"),
                ("Burnt",      "Food"),
                ("Dried",      "Food"),
                ("Fried",      "Food"),
                ("Crunchies",  "Food"),
                ("Roast",      "Food"),
                ("Mushroom",   "Food"),
                ("Potato",     "Food"),
                ("Onion",      "Food"),
                ("Potion",     "Potions"),
                ("Infusion",   "Potions"),
                ("Herb",       "Herbs"),
                ("Grimy",      "Grimy Herbs"),
                ("Clean",      "Herbs"),
                ("Skillcape",  "Skillcapes"),
                ("Tome",       "Tombs"),
                ("Cape",       "Capes"),
                ("Cloak",      "Capes"),
                ("TEST",       "TEST"),
            };

            foreach (var (key, cat) in categories)
                if (name.Contains(key, StringComparison.OrdinalIgnoreCase))
                    return cat;

            return "Basic Item";
        }

        private void WriteItemJson(List<ItemEntry> items)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(_outputItemJson)!);
            var opts = new JsonSerializerOptions { WriteIndented = true };
            File.WriteAllText(
                _outputItemJson,
                JsonSerializer.Serialize(items, opts),
                Encoding.UTF8);
        }

        private void ExtractIcons(DefaultFileProvider provider, HashSet<string> referencedIcons)
        {
            Directory.CreateDirectory(_outputIconsDir);

            var iconPaths = provider.Files.Keys
                .Where(p =>
                    p.Contains("/Art/UI/Icons/", StringComparison.OrdinalIgnoreCase) &&
                    p.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase) &&
                    !IsBuildingIcon(Path.GetFileNameWithoutExtension(p)))
                .ToList();

            Console.WriteLine($"      Found {iconPaths.Count} icon assets (building icons excluded).");

            int copied = 0, skipped = 0;

            foreach (var path in iconPaths)
            {
                try
                {
                    var textureName = Path.GetFileNameWithoutExtension(path) + ".png";
                    var outPath     = Path.Combine(_outputIconsDir, textureName);

                    var package = provider.LoadPackage(path);
                    if (package == null) { skipped++; continue; }

                    UTexture2D? texture = null;
                    foreach (var exportLazy in package.ExportsLazy)
                    {
                        if (exportLazy.Value is UTexture2D t) { texture = t; break; }
                    }
                    if (texture == null) { skipped++; continue; }

                    var bitmap = texture.Decode();
                    if (bitmap == null) { skipped++; continue; }

                    var pngBytes = bitmap.Encode(ETextureFormat.Png, false, out _);
                    File.WriteAllBytes(outPath, pngBytes);
                    copied++;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"      Skip {Path.GetFileName(path)}: {ex.Message}");
                    skipped++;
                }
            }

            Console.WriteLine($"      Copied: {copied}  Skipped: {skipped}");

            var missingList = referencedIcons
                .Where(icon =>
                    icon != "ICON PLACEHOLDER.png" &&
                    !File.Exists(Path.Combine(_outputIconsDir, icon)))
                .OrderBy(x => x)
                .ToList();

            var missingPath = Path.Combine(
                Path.GetDirectoryName(_outputItemJson)!, "..", "MissingIcons.txt");

            if (missingList.Count > 0)
            {
                File.WriteAllLines(missingPath, missingList);
                Console.WriteLine($"      WARNING: {missingList.Count} missing icons — see MissingIcons.txt");
            }
            else
            {
                File.WriteAllText(missingPath, "No missing icons found." + Environment.NewLine);
                Console.WriteLine("      No missing icons.");
            }
        }

        private static bool IsBuildingIcon(string name)
        {
            var lower = name.ToLowerInvariant();
            return BuildingKeywords.Any(k => lower.Contains(k));
        }

        private void DeprecateUnusedIcons(HashSet<string> referencedIcons)
        {
            if (!Directory.Exists(_outputIconsDir)) return;
            Directory.CreateDirectory(_outputIconsOldDir);

            var existing = Directory.GetFiles(
                _outputIconsDir, "*.png", SearchOption.TopDirectoryOnly);

            int moved = 0, already = 0;

            foreach (var file in existing)
            {
                var name = Path.GetFileName(file);
                if (referencedIcons.Contains(name)) continue;

                var dest = Path.Combine(_outputIconsOldDir, name);
                if (File.Exists(dest))
                {
                    File.Delete(file);
                    already++;
                }
                else
                {
                    File.Move(file, dest);
                    moved++;
                }
            }

            Console.WriteLine($"      Deprecated: {moved} moved to old/  ({already} already deprecated)");
        }
    }
}