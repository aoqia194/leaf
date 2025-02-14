package dev.aoqia;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.ListIterator;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import com.fasterxml.jackson.databind.DatabindException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.semver4j.Semver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Main {
    public static final Logger LOGGER = LoggerFactory.getLogger("ManifestGenerator");
    public static final ObjectMapper MAPPER = new ObjectMapper();
    public static final DateTimeFormatter DEPOT_DATE_FORMATTER = DateTimeFormatter.ofPattern(
            "yyyy-MM-dd HH:mm:ss")
        .withZone(ZoneOffset.UTC);
    public static final DateTimeFormatter NOW_DATE_FORMATTER = DateTimeFormatter.ofPattern(
            "yyyy-MM-dd'T'HH:mm:ssZ")
        .withZone(ZoneOffset.UTC);
    public static final HexFormat HEXFORMAT = HexFormat.of();
    public static final String REPOSITORY_URL = "https://github.com/aoqia194/leaf/raw/refs/heads" +
                                                "/main";
    public static final String INDEXES_URL = REPOSITORY_URL + "/indexes";
    public static final String MANIFESTS_URL = REPOSITORY_URL + "/manifests";
    public static final String[] ENV_SUBDIRS = { "client", "server" };
    public static final String[] CLIENT_PLATFORM_SUBDIRS = { "mac", "linux", "win" };
    public static final String[] CLIENT_DEPOT_SUBDIRS = { "108602", "108603", "108604" };
    public static final String[] SERVER_PLATFORM_SUBDIRS = { "common", "mac", "linux", "win" };
    public static final String[] SERVER_DEPOT_SUBDIRS = { "380871", "380872", "380873", "380874" };
    public static final String VERSION_MANIFEST_JSON = "version_manifest.json";
    public static final String GAME_VERSIONS_JSON = "game_versions.json";
    public static final Pattern DEPOT_HEADER_REGEX = Pattern.compile(
        "^Content Manifest for Depot (\\d+)$|^Manifest ID \\/ date\\s*\\:\\s*(\\d+)\\s*\\/\\s*" +
        "([^\\n]+)$|^Total " +
        "number of files\\s*\\:\\s*(\\d+)$|^Total number of chunks\\s*\\:\\s*(\\d+)$|^Total bytes" +
        " on disk\\s*\\:\\s*" +
        "(\\d+)$|^Total bytes compressed\\s*\\:\\s*(\\d+)$");
    public static final Pattern DEPOT_ENTRY_REGEX = Pattern.compile(
        "(?:^ *(\\d+)\\s*(\\d+)\\s*(\\w+)\\s*(\\d+)\\s*([^\\n]*))");
    public static MessageDigest SHA1_DIGEST;
    private static Path outputPath;
    private static Path depotsPath;
    private static boolean force;
    private static Path manifestsPath;
    private static Path indexesPath;
    private static VersionTable versionTable;

    public static void main(String[] args) {
        depotsPath = Path.of(System.getProperty("leaf.depotsPath"));
        outputPath = Path.of(System.getProperty("leaf.rootPath"));
        force = Boolean.parseBoolean(System.getProperty("leaf.force", "false"));

        if (!depotsPath.toFile().exists() || !outputPath.toFile().exists()) {
            throw new RuntimeException("The depots path or the output path doesn't exist");
        }

        try {
            SHA1_DIGEST = MessageDigest.getInstance("SHA-1");
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }

        manifestsPath = outputPath.resolve("manifests");
        indexesPath = outputPath.resolve("indexes");

        // Create all the subdirs if needed.
        for (String platform : CLIENT_PLATFORM_SUBDIRS) {
            try {
                Files.createDirectories(manifestsPath
                    .resolve(ENV_SUBDIRS[0])
                    .resolve(platform));
                Files.createDirectories(indexesPath
                    .resolve(ENV_SUBDIRS[0])
                    .resolve(platform));
            } catch (IOException e) {
                LOGGER.error("Failed to create manifest output directory for {}", platform, e);
                throw new RuntimeException(e);
            }
        }
        for (String platform : SERVER_PLATFORM_SUBDIRS) {
            try {
                Files.createDirectories(manifestsPath
                    .resolve(ENV_SUBDIRS[1])
                    .resolve(platform));
                Files.createDirectories(indexesPath
                    .resolve(ENV_SUBDIRS[1])
                    .resolve(platform));
            } catch (IOException e) {
                LOGGER.error("Failed to create manifest output directory for {}", platform, e);
                throw new RuntimeException(e);
            }
        }

        LOGGER.info("Hi!! I am going to generate some manifests for you 💖");
        LOGGER.debug("depotsPath: {}", depotsPath);
        LOGGER.debug("outputPath: {}", outputPath);
        LOGGER.debug("force: {}", force);

        try {
            versionTable = MAPPER.readValue(outputPath.resolve(GAME_VERSIONS_JSON).toFile(),
                VersionTable.class);
            generateClientManifests();
            generateServerManifests();
        } catch (IOException e) {
            LOGGER.error("Failed to parse version table and generate manifests.", e);
            throw new RuntimeException(e);
        }
    }

    public static void generateClientManifests() throws IOException {
        for (int i = 0; i < CLIENT_DEPOT_SUBDIRS.length; i++) {
            String depotId = CLIENT_DEPOT_SUBDIRS[i];

            final Path manifestsDir = manifestsPath.resolve(ENV_SUBDIRS[0])
                .resolve(CLIENT_PLATFORM_SUBDIRS[i]);

            /*
             * Contains a list of manifests that only contain the latest manifest for each version.
             * For example, if is a game version with 2 manifests with the same depot id/
             */
            HashMap<String, DepotManifest> uniqueManifests = new HashMap<>();

            LOGGER.info("Fetching latest manifests...");
            try (Stream<Path> buildStream = Files.walk(depotsPath.resolve(depotId))
                .filter(Files::isRegularFile)
                .filter(path -> !path.toFile().getParentFile().getName().startsWith("."))) {
                for (Path depotFile : buildStream.toList()) {
                    LOGGER.debug("Found depot manifest at path {}", depotFile);

                    DepotManifest manifest = parseDepotManifest(depotFile);
                    String version = getManifestGameVersion(manifest).toString();
                    if (!uniqueManifests.containsKey(version) ||
                        OffsetDateTime.parse(manifest.manifestDate)
                            .isAfter(
                                OffsetDateTime.parse(uniqueManifests.get(version).manifestDate))) {
                        LOGGER.debug(
                            "Manifest was unique or contained a later build of the version.");
                        uniqueManifests.put(version, manifest);
                    }
                }
            }

            LOGGER.info("Generating client manifests for depot {}", depotId);
            for (String ver : uniqueManifests.keySet()) {
                DepotManifest manifest = uniqueManifests.get(ver);
                Semver version = Semver.parse(ver);

                LOGGER.debug("Generating (depotId={},manifestId={},version={})",
                    depotId,
                    manifest.manifestId,
                    version);

                final File indexesFile = indexesPath.resolve(ENV_SUBDIRS[0])
                    .resolve(CLIENT_PLATFORM_SUBDIRS[i])
                    .resolve(version + ".json")
                    .toFile();

                writeIndexesManifest(manifest, indexesFile);
                writeLauncherManifest(manifest, version, indexesFile, manifestsDir);
                writeVersionManifest(manifest, version, manifestsDir);
            }
        }
    }

    public static void generateServerManifests() throws IOException {
        for (int i = 0; i < SERVER_DEPOT_SUBDIRS.length; i++) {
            String depotId = SERVER_DEPOT_SUBDIRS[i];

            final Path manifestsDir = manifestsPath.resolve(ENV_SUBDIRS[1])
                .resolve(SERVER_PLATFORM_SUBDIRS[i]);

            // Contains a list of manifests that only contain the latest manifest for each version.
            HashMap<String, DepotManifest> uniqueManifests = new HashMap<>();

            LOGGER.info("Fetching latest manifests...");
            try (Stream<Path> buildStream = Files.walk(depotsPath.resolve(depotId))
                .filter(Files::isRegularFile)
                .filter(path -> !path.toFile().getParentFile().getName().startsWith("."))) {
                for (Path depotFile : buildStream.toList()) {
                    LOGGER.debug("Found depot manifest at path {}", depotFile);

                    DepotManifest manifest = parseDepotManifest(depotFile);
                    String version = getManifestGameVersion(manifest).toString();
                    if (!uniqueManifests.containsKey(version) ||
                        OffsetDateTime.parse(manifest.manifestDate)
                            .isAfter(
                                OffsetDateTime.parse(uniqueManifests.get(version).manifestDate))) {
                        LOGGER.debug(
                            "Manifest was unique or contained a later build of the version.");
                        uniqueManifests.put(version, manifest);
                    }
                }
            }

            LOGGER.info("Generating server manifests for depot {}", depotId);
            for (String ver : uniqueManifests.keySet()) {
                DepotManifest manifest = uniqueManifests.get(ver);
                Semver version = Semver.parse(ver);

                LOGGER.debug("Generating (depotId={},manifestId={},version={})",
                    depotId,
                    manifest.manifestId,
                    version);

                final File indexesFile = indexesPath.resolve(ENV_SUBDIRS[1])
                    .resolve(SERVER_PLATFORM_SUBDIRS[i])
                    .resolve(version + ".json")
                    .toFile();

                writeIndexesManifest(manifest, indexesFile);
                writeLauncherManifest(manifest, version, indexesFile, manifestsDir);
                writeVersionManifest(manifest, version, manifestsDir);
            }
        }
    }

    private static DepotManifest parseDepotManifest(Path depotFile) throws IOException {
        ListIterator<String> lines = Files.readAllLines(depotFile).listIterator();
        Matcher matcher = DEPOT_HEADER_REGEX.matcher(lines.next());

        String depotId = matcher.find() ? matcher.group(1) : "";
        lines.next();

        String manifestIdDate = lines.next();
        String manifestId = matcher.reset(manifestIdDate).find() ? matcher.group(2) : "";
        matcher.reset(manifestIdDate);
        String manifestDate;
        try {
            manifestDate = OffsetDateTime.parse(matcher.find()
                    ? matcher.group(3) : "", DEPOT_DATE_FORMATTER)
                .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
        } catch (DateTimeParseException e) {
            throw new RuntimeException("Failed to parse manifest date and time!", e);
        }

        String numFiles = matcher.reset(lines.next()).find() ? matcher.group(4) : "";
        String numChunks = matcher.reset(lines.next()).find() ? matcher.group(5) : "";
        String bytesDisk = matcher.reset(lines.next()).find() ? matcher.group(6) : "";
        String bytesCompressed = matcher.reset(lines.next()).find() ? matcher.group(7) : "";

        if (depotId.isEmpty() || manifestId.isEmpty() || numFiles.isEmpty() ||
            numChunks.isEmpty() ||
            bytesDisk.isEmpty() || bytesCompressed.isEmpty()) {
            LOGGER.error("Failed to parse depot manifest. This is bad!");
            throw new RuntimeException("Failed to parse depot manifest");
        }

        DepotManifest manifest = new DepotManifest();
        manifest.depotId = depotId;
        manifest.manifestId = manifestId;
        manifest.manifestDate = manifestDate;
        manifest.numFiles = numFiles;
        manifest.numChunks = numChunks;
        manifest.bytesDisk = bytesDisk;
        manifest.bytesCompressed = bytesCompressed;
        manifest.entries = new HashMap<>();

        // Advance past the blanks
        lines.next();
        lines.next();

        matcher.usePattern(DEPOT_ENTRY_REGEX).reset();
        while (lines.hasNext()) {
            String line = lines.next();

            if (!matcher.reset(line).find()) {
                LOGGER.debug("Failed to find match on line {}", line);
                continue;
            }

            // If size of entry is 0, it's a directory. Don't store directories.
            String size = matcher.group(1);
            if (size.startsWith("0")) {
                continue;
            }

            String chunks = matcher.group(2);
            String sha1 = matcher.group(3);
            String flags = matcher.group(4);
            String name = matcher.group(5);

            DepotManifest.Entry entry = new DepotManifest.Entry();
            entry.chunks = chunks;
            entry.sha1 = sha1;
            entry.size = size;
            entry.flags = flags;

            manifest.entries.put(name, entry);
        }

        return manifest;
    }

    /**
     * Gets the game version from a manifest by parsing the version table and finding which version
     * it belongs to.
     *
     * @param manifest The depot manifest to check against.
     * @return The Semver version string.
     */
    private static Semver getManifestGameVersion(DepotManifest manifest) {
        Semver gameVersion = null;

        for (String version : versionTable.versions.keySet()) {
            if (versionTable.versions.get(version).manifests.contains(manifest.manifestId)) {
                gameVersion = Semver.parse(version);
                break;
            }
        }

        return gameVersion;
    }

    public static void writeIndexesManifest(DepotManifest depot, File out) throws IOException {
        LOGGER.info("Generating indexes manifest.");
        if (!force && out.exists()) {
            LOGGER.info("Index manifest already exists.");
            return;
        }

        // Rebuild entries into index objects
        HashMap<String, AssetIndexManifest.AssetIndex> objects = new HashMap<>();
        for (int i = 0; i < depot.entries.size(); i++) {
            String key = depot.entries.keySet().toArray()[i].toString();
            DepotManifest.Entry value = depot.entries.get(key);

            AssetIndexManifest.AssetIndex manifest = new AssetIndexManifest.AssetIndex();
            manifest.hash = value.sha1;
            manifest.size = value.size;

            objects.put(key, manifest);
        }

        AssetIndexManifest manifest = new AssetIndexManifest();
        manifest.objects = objects;

        MAPPER.writeValue(out, manifest);
    }

    private static void writeLauncherManifest(DepotManifest depot, Semver gameVersion,
        File assetIndexFile, Path out) throws IOException {
        LOGGER.info("Generating launcher manifest.");

        assert assetIndexFile.exists();

        Path outFile = out.resolve(gameVersion + ".json");
        File f = outFile.toFile();

        OffsetDateTime depotManifestDate = OffsetDateTime.parse(depot.manifestDate,
            DateTimeFormatter.ISO_OFFSET_DATE_TIME);

        // Check if manifest exist and check date since
        // versions can be the same id but different depots.
        if (!force && f.exists()) {
            try {
                LauncherManifest manifest = MAPPER.readValue(f, LauncherManifest.class);

                OffsetDateTime launcherManifestDate = OffsetDateTime.parse(manifest.releaseTime,
                    DateTimeFormatter.ISO_OFFSET_DATE_TIME);
                if (launcherManifestDate.isBefore(depotManifestDate)) {
                    LOGGER.info("Found launcher manifest with same version but older release date. "
                                + "Overwriting with newer version...");
                } else {
                    LOGGER.debug("Launcher manifest already exists with version {} at path {}.",
                        gameVersion,
                        out);
                    return;
                }
            } catch (DatabindException e) {
                LOGGER.warn("Failed to parse existing launcher manifest. Nuking the file.");
                if (!f.delete()) {
                    throw new RuntimeException("Failed to delete existing launcher manifest.");
                }
            }
        }

        String env = getEnvFromPlatformDir(out);
        String os = getOsFromPlatformDir(out);

        byte[] bytes = Files.readAllBytes(assetIndexFile.toPath());
        String sha1 = HEXFORMAT.formatHex(SHA1_DIGEST.digest(bytes));
        String url = "%s/%s/%s/%s.json".formatted(INDEXES_URL, env, os, gameVersion.toString());

        LauncherManifest.AssetIndex assetIndex = new LauncherManifest.AssetIndex();
        assetIndex.sha1 = sha1;
        assetIndex.size = bytes.length;
        assetIndex.url = url;

        VersionTable.Version version = versionTable.versions.get(gameVersion.toString());

        LauncherManifest manifest = new LauncherManifest();
        manifest.assetIndex = assetIndex;

        // If no arguments found, check inherited version's args.
        // If no inherited version, just use the first one found.
        LauncherManifest.Args arguments = null;
        if (version.arguments != null) {
            arguments = version.arguments;
        } else if (!version.inherits.isEmpty()) {
            arguments = versionTable.versions.get(version.inherits).arguments;
        } else {
            for (final var entry : versionTable.versions.entrySet()) {
                final var ver = entry.getValue();
                if (ver.arguments != null) {
                    arguments = ver.arguments;
                    break;
                }
            }
        }

        manifest.arguments = arguments;
        manifest.libraries = (version.libraries != null) ? version.libraries : List.of();
        manifest.mainClass =
            env.equals("client") ? "zombie.gameStates.MainScreenState" : "zombie.network.Server";
        manifest.releaseTime = depotManifestDate.toString();
        manifest.time = OffsetDateTime.now(ZoneOffset.UTC)
            .truncatedTo(ChronoUnit.SECONDS)
            .toString();
        manifest.id = gameVersion.toString();

        manifest.javaVersion = "17";
        if (gameVersion.isGreaterThanOrEqualTo("41.78.16")) {
            manifest.javaVersion = "17";
        }

        MAPPER.writeValue(f, manifest);
    }

    public static void writeVersionManifest(DepotManifest depot, Semver gameVersion,
        Path out) throws IOException {
        LOGGER.info("Generating version manifest.");

        File launcherManifest = out.resolve(gameVersion + ".json").toFile();
        File versionManifest = out.resolve(VERSION_MANIFEST_JSON).toFile();

        String env = getEnvFromPlatformDir(out);
        String os = getOsFromPlatformDir(out);

        // Launcher manifest is guaranteed to exist by this point.
        // We can read it and calculate hash etc.
        byte[] bytes = Files.readAllBytes(launcherManifest.toPath());
        String sha1 = HEXFORMAT.formatHex(SHA1_DIGEST.digest(bytes));

        // Create dummy version entry (to be inserted later).
        VersionManifest.Version version = new VersionManifest.Version();
        version.id = gameVersion.toString();
        version.url = "%s/%s/%s/%s.json".formatted(MANIFESTS_URL, env, os, gameVersion.toString());
        version.sha1 = sha1;
        version.time = OffsetDateTime.now(ZoneOffset.UTC)
            .truncatedTo(ChronoUnit.SECONDS)
            .toString();
        version.releaseTime = depot.manifestDate;

        // Check for invalid data if the file exists and delete if found.
        if (versionManifest.exists()) {
            try {
                MAPPER.readValue(versionManifest, VersionManifest.class);
            } catch (DatabindException e) {
                LOGGER.warn(
                    "Existing version manifest could not be parsed. Deleting to overwrite.");
                if (!versionManifest.delete()) {
                    throw new RuntimeException("Failed to delete existing version manifest.");
                }
            }

            // Properly edit existing manifest below. The else clause is creating a new one.

            VersionManifest manifest = MAPPER.readValue(versionManifest, VersionManifest.class);

            final boolean isUnstable = gameVersion.getVersion().contains("unstable");
            if (isUnstable && (manifest.latest.unstable == null ||
                               gameVersion.isGreaterThan(manifest.latest.unstable))) {
                manifest.latest.unstable = gameVersion.getVersion();
            } else if (!isUnstable && (manifest.latest.release == null ||
                                       gameVersion.isGreaterThan(manifest.latest.release))) {
                manifest.latest.release = gameVersion.getVersion();
            }

            if (gameVersion.isGreaterThan(manifest.versions.getFirst().id)) {
                LOGGER.info("Version found was the latest, adding to front of list.");
                manifest.versions.addFirst(version);
            } else if (gameVersion.isLowerThan(manifest.versions.getLast().id)) {
                LOGGER.info("Version found was the oldest, adding to end of list.");
                manifest.versions.addLast(version);
            } else {
                boolean update = false;
                int idx = -1;

                // Checking if the version exists already.
                for (int i = 0; i < manifest.versions.size(); ++i) {
                    var ver = manifest.versions.get(i);
                    if (ver.id.equals(gameVersion.toString())) {
                        idx = i;
                        break;
                    }
                }

                // If it doesn't exist already, just add new one.
                if (idx == -1) {
                    for (int i = 0; i < manifest.versions.size(); ++i) {
                        if (i == manifest.versions.size() - 1) {
                            LOGGER.warn(
                                "Reached end of list while trying to figure out where to put " +
                                "version." +
                                "Forcing add at the end of list");
                            manifest.versions.addLast(version);
                            update = true;
                            break;
                        }

                        var curr = Semver.parse(manifest.versions.get(i).id);
                        var next = Semver.parse(manifest.versions.get(i + 1).id);
                        assert curr != null;
                        assert next != null;

                        if (gameVersion.isLowerThan(curr) && gameVersion.isGreaterThan(next)) {
                            manifest.versions.add(i + 1, version);
                            update = true;
                            break;
                        }
                    }
                } else {
                    // Update older versions with newer manifest.
                    var ver = manifest.versions.get(idx);
                    OffsetDateTime versionDate = OffsetDateTime.parse(version.releaseTime);
                    OffsetDateTime versionEntryDate = OffsetDateTime.parse(ver.releaseTime);

                    // The version can be the same but have a newer manifest (thanks TIS).
                    if (ver.id.equals(gameVersion.toString()) &&
                        (versionEntryDate.isBefore(versionDate) ||
                         versionEntryDate.isEqual(versionDate))) {
                        LOGGER.info("Version found in manifest is the same but older manifest.");

                        ver.id = version.id;
                        ver.releaseTime = version.releaseTime;
                        ver.sha1 = version.sha1;
                        ver.time = version.time;
                        ver.url = version.url;

                        update = true;
                    }
                }

                if (!update) {
                    LOGGER.info(
                        "Version manifest already exists and contains no versions to update.");
                    return;
                }
            }

            MAPPER.writeValue(versionManifest, manifest);
        } else {
            // New file, just write and finished!
            List<VersionManifest.Version> versions = List.of(version);

            VersionManifest manifest = new VersionManifest();
            manifest.latest = new VersionManifest.LatestVersion(gameVersion.getVersion());
            manifest.versions = versions;

            MAPPER.writeValue(versionManifest, manifest);
        }
    }

    public static String getEnvFromPlatformDir(Path dir) {
        return dir.getParent().getFileName().toString();
    }

    public static String getOsFromPlatformDir(Path dir) {
        return dir.getFileName().toString();
    }
}
