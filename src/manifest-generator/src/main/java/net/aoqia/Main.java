package net.aoqia;

import java.io.File;
import java.io.IOException;
import java.net.URISyntaxException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.*;
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
    public static final DateTimeFormatter DEPOT_DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
        .withZone(ZoneOffset.UTC);
    public static final DateTimeFormatter NOW_DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssZ")
        .withZone(ZoneOffset.UTC);
    public static final HexFormat HEXFORMAT = HexFormat.of();
    public static final String REPOSITORY_URL = "https://github.com/aoqia194/leaf/raw/refs/heads/main";
    public static final String INDEXES_URL = REPOSITORY_URL + "/indexes";
    public static final String MANIFESTS_URL = REPOSITORY_URL + "/manifests";
    public static final String[] ENV_SUBDIRS = { "client", "server" };
    public static final String[] CLIENT_PLATFORM_SUBDIRS = { "mac", "linux", "win" };
    public static final String[] CLIENT_DEPOT_SUBDIRS = { "108602", "108603", "108604" };
    public static final String[] SERVER_PLATFORM_SUBDIRS = { "common", "mac", "linux", "win" };
    public static final String[] SERVER_DEPOT_SUBDIRS = { "380871", "380872", "380873", "380874" };
    public static final String VERSION_MANIFEST_JSON = "version_manifest.json";
    public static final String VERSION_TABLE_JSON = "version_table.json";
    public static final Pattern DEPOT_HEADER_REGEX = Pattern.compile(
        "^Content Manifest for Depot (\\d+)$|^Manifest ID \\/ date\\s*\\:\\s*(\\d+)\\s*\\/\\s*([^\\n]+)$|^Total " +
        "number of files\\s*\\:\\s*(\\d+)$|^Total number of chunks\\s*\\:\\s*(\\d+)$|^Total bytes on disk\\s*\\:\\s*" +
        "(\\d+)$|^Total bytes compressed\\s*\\:\\s*(\\d+)$");
    public static final Pattern DEPOT_ENTRY_REGEX = Pattern.compile(
        "(?:^ *(\\d+)\\s*(\\d+)\\s*(\\w+)\\s*(\\d+)\\s*([^\\n]*))");
    private static final VersionManifest.LatestVersion latestVersion = new VersionManifest.LatestVersion();
    public static MessageDigest SHA1_DIGEST;
    private static Path outputPath;
    private static Path depotsPath;
    private static boolean force;
    private static Path manifestsPath;
    private static Path indexesPath;
    private static VersionTable versionTable;
    private static Semver gameVersion;

    public static void main(String[] args) {
        depotsPath = Path.of(System.getProperty("leaf.depotsPath"));
        outputPath = Path.of(System.getProperty("leaf.rootPath"));
        force = Boolean.parseBoolean(System.getProperty("leaf.force"));

        if (!depotsPath.toFile().exists() || !outputPath.toFile().exists()) {
            throw new RuntimeException("The depots path or the output path doesn't exist");
        }

        Path jarPath;
        try {
            jarPath = new File(Main.class
                .getProtectionDomain()
                .getCodeSource()
                .getLocation()
                .toURI()).toPath().getParent();
        } catch (URISyntaxException e) {
            throw new RuntimeException(e);
        }

        if (jarPath == null) {
            throw new RuntimeException("Failed to find the path of the running jar!");
        }

        try {
            SHA1_DIGEST = MessageDigest.getInstance("SHA-1");
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }

        manifestsPath = getOutputPath().resolve("manifests");
        indexesPath = getOutputPath().resolve("indexes");

        // Create all the subdirs if needed.
        for (String platform : CLIENT_PLATFORM_SUBDIRS) {
            try {
                Files.createDirectories(getManifestsPath()
                    .resolve(ENV_SUBDIRS[EnvType.CLIENT.ordinal()])
                    .resolve(platform));
                Files.createDirectories(getIndexesPath()
                    .resolve(ENV_SUBDIRS[EnvType.CLIENT.ordinal()])
                    .resolve(platform));
            } catch (IOException e) {
                LOGGER.error("Failed to create manifest output directory for {}", platform, e);
                throw new RuntimeException(e);
            }
        }
        for (String platform : SERVER_PLATFORM_SUBDIRS) {
            try {
                Files.createDirectories(getManifestsPath()
                    .resolve(ENV_SUBDIRS[EnvType.SERVER.ordinal()])
                    .resolve(platform));
                Files.createDirectories(getIndexesPath()
                    .resolve(ENV_SUBDIRS[EnvType.SERVER.ordinal()])
                    .resolve(platform));
            } catch (IOException e) {
                LOGGER.error("Failed to create manifest output directory for {}", platform, e);
                throw new RuntimeException(e);
            }
        }

        LOGGER.info("Hi!! I am going to generate some manifests for you 💖");
        LOGGER.debug("depotsPath: {}", getDepotsPath());
        LOGGER.debug("outputPath: {}", getOutputPath());
        LOGGER.debug("force: {}", isForce());

        try {
            versionTable = MAPPER.readValue(getOutputPath().resolve(VERSION_TABLE_JSON).toFile(), VersionTable.class);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }

        generateManifests();
    }

    public static Path getOutputPath() {
        return outputPath;
    }

    public static Path getManifestsPath() {
        return manifestsPath;
    }

    public static Path getIndexesPath() {
        return indexesPath;
    }

    public static Path getDepotsPath() {
        return depotsPath;
    }

    public static boolean isForce() {
        return force;
    }

    public static void generateManifests() {
        for (int i = 0; i < CLIENT_DEPOT_SUBDIRS.length; i++) {
            String depotId = CLIENT_DEPOT_SUBDIRS[i];

            Semver lastIndexVersion = null;
            OffsetDateTime lastIndexDate = null;

            LOGGER.info("Generating client manifests for depot {}", depotId);
            try (Stream<Path> buildStream = Files.walk(getDepotsPath().resolve(depotId))
                .filter(Files::isRegularFile)
                .filter(path -> !path.toFile().getParentFile().getName().startsWith("."))) {
                for (Path depotFile : buildStream.toList()) {
                    LOGGER.debug("Found depot manifest at path {}", depotFile);

                    DepotManifest depotManifest = parseDepotManifest(depotFile);
                    getLatestVersions(depotManifest);

                    generateIndexesManifest(depotManifest, getIndexesPath()
                        .resolve(ENV_SUBDIRS[EnvType.CLIENT.ordinal()])
                        .resolve(CLIENT_PLATFORM_SUBDIRS[i]), lastIndexVersion, lastIndexDate);
                    lastIndexVersion = getGameVersion();
                    lastIndexDate = OffsetDateTime.parse(depotManifest.manifestDate);

                    generateLauncherManifest(depotManifest, getIndexesPath()
                            .resolve(ENV_SUBDIRS[EnvType.CLIENT.ordinal()])
                            .resolve(CLIENT_PLATFORM_SUBDIRS[i]).resolve(getGameVersion() + ".json")
                            .toFile(),
                        getManifestsPath()
                            .resolve(ENV_SUBDIRS[EnvType.CLIENT.ordinal()])
                            .resolve(CLIENT_PLATFORM_SUBDIRS[i]));
                    generateVersionManifest(depotManifest, getManifestsPath()
                        .resolve(ENV_SUBDIRS[EnvType.CLIENT.ordinal()])
                        .resolve(CLIENT_PLATFORM_SUBDIRS[i]));
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        for (int i = 0; i < SERVER_DEPOT_SUBDIRS.length; i++) {
            String depotId = SERVER_DEPOT_SUBDIRS[i];

            Semver lastIndexVersion = null;
            OffsetDateTime lastIndexDate = null;

            LOGGER.info("Generating server manifests for depot {}", depotId);
            try (Stream<Path> buildStream = Files.walk(getDepotsPath().resolve(depotId))
                .filter(Files::isRegularFile)
                .filter(path -> !path.toFile().getParentFile().getName().startsWith("."))) {
                for (Path depotFile : buildStream.toList()) {
                    LOGGER.debug("Found depot manifest at path {}", depotFile);

                    DepotManifest depotManifest = parseDepotManifest(depotFile);
                    getLatestVersions(depotManifest);

                    generateIndexesManifest(depotManifest, getIndexesPath()
                        .resolve(ENV_SUBDIRS[EnvType.SERVER.ordinal()])
                        .resolve(SERVER_PLATFORM_SUBDIRS[i]), lastIndexVersion, lastIndexDate);
                    lastIndexVersion = getGameVersion();
                    lastIndexDate = OffsetDateTime.parse(depotManifest.manifestDate);

                    generateLauncherManifest(depotManifest, getIndexesPath()
                            .resolve(ENV_SUBDIRS[EnvType.SERVER.ordinal()])
                            .resolve(SERVER_PLATFORM_SUBDIRS[i]).resolve(getGameVersion() + ".json")
                            .toFile(),
                        getManifestsPath()
                            .resolve(ENV_SUBDIRS[EnvType.SERVER.ordinal()])
                            .resolve(SERVER_PLATFORM_SUBDIRS[i]));
                    generateVersionManifest(depotManifest, getManifestsPath()
                        .resolve(ENV_SUBDIRS[EnvType.SERVER.ordinal()])
                        .resolve(SERVER_PLATFORM_SUBDIRS[i]));
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
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
                ? matcher.group(3) : "", DEPOT_DATE_FORMATTER).format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
        } catch (DateTimeParseException e) {
            throw new RuntimeException("Failed to parse manifest date and time!", e);
        }

        String numFiles = matcher.reset(lines.next()).find() ? matcher.group(4) : "";
        String numChunks = matcher.reset(lines.next()).find() ? matcher.group(5) : "";
        String bytesDisk = matcher.reset(lines.next()).find() ? matcher.group(6) : "";
        String bytesCompressed = matcher.reset(lines.next()).find() ? matcher.group(7) : "";

        if (depotId.isEmpty() || manifestId.isEmpty() || numFiles.isEmpty() || numChunks.isEmpty() ||
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

    private static void getLatestVersions(DepotManifest depotManifest) {
        for (String version : getVersionTable().versions.keySet()) {
            if (!version.contains("-unstable") && latestVersion.release == null) {
                latestVersion.release = version;
            }

            if (getVersionTable().versions.get(version).manifests.contains(depotManifest.manifestId)) {
                gameVersion = Semver.parse(version);
                break;
            }
        }

        for (String version : getVersionTable().versions.keySet()) {
            if (version.contains("-unstable") && latestVersion.unstable == null) {
                latestVersion.unstable = version;
            }

            if (gameVersion == null &&
                getVersionTable().versions.get(version).manifests.contains(depotManifest.manifestId)) {
                gameVersion = Semver.parse(version);
                break;
            }
        }
    }

    public static void generateIndexesManifest(DepotManifest depot, Path out, Semver lastIndexVersion,
        OffsetDateTime lastIndexDate) throws IOException {
        LOGGER.info("Generating indexes manifest.");

        File f = out.resolve(getGameVersion() + ".json").toFile();
        // If lastIndexDate is null, it means this is the first index of the depot.
        if (lastIndexVersion != null &&
            lastIndexDate != null &&
            lastIndexVersion.isEqualTo(getGameVersion()) &&
            lastIndexDate.isAfter(OffsetDateTime.parse(depot.manifestDate)) &&
            !isForce() &&
            f.exists()) {
            LOGGER.info("Index manifest already exists and not forcing. The date of this index is older, so skip it.");
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

        MAPPER.writeValue(f, manifest);
    }

    public static Semver getGameVersion() {
        return gameVersion;
    }

    private static void generateLauncherManifest(DepotManifest depot, File assetIndexFile, Path out) throws
        IOException {
        LOGGER.info("Generating launcher manifest.");

        assert assetIndexFile.exists();

        Path outFile = out.resolve(getGameVersion() + ".json");
        File f = outFile.toFile();

        OffsetDateTime depotManifestDate = OffsetDateTime.parse(depot.manifestDate,
            DateTimeFormatter.ISO_OFFSET_DATE_TIME);

        // Check if manifest exist and check date since
        // versions can be the same id but different depots.
        if (!isForce() && f.exists()) {
            try {
                LauncherManifest manifest = MAPPER.readValue(f, LauncherManifest.class);

                OffsetDateTime launcherManifestDate = OffsetDateTime.parse(manifest.releaseTime,
                    DateTimeFormatter.ISO_OFFSET_DATE_TIME);
                if (launcherManifestDate.isBefore(depotManifestDate) ||
                    launcherManifestDate.isEqual(depotManifestDate)) {
                    LOGGER.info("Found launcher manifest with same version but older release date."
                                + "Overwriting with newer version...");
                } else {
                    LOGGER.debug("Launcher manifest already exists with version {} at path {}.", getGameVersion(), out);
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
        String url = "%s/%s/%s/%s.json".formatted(INDEXES_URL, env, os, getGameVersion().toString());

        LauncherManifest.AssetIndex assetIndex = new LauncherManifest.AssetIndex();
        assetIndex.sha1 = sha1;
        assetIndex.size = bytes.length;
        assetIndex.url = url;

        JavaVersion javaVersion = new JavaVersion();
        javaVersion.component = "java-runtime-delta";
        javaVersion.majorVersion = 0;

        if (getGameVersion().isGreaterThanOrEqualTo("41.78.16")) {
            javaVersion.majorVersion = 17;
        }

        LauncherManifest manifest = new LauncherManifest();
        manifest.assetIndex = assetIndex;
        manifest.javaVersion = javaVersion;

        LauncherManifest.Args arguments = new LauncherManifest.Args();
        arguments.game = List.of();
        arguments.jvm = List.of();

        manifest.arguments = arguments;
        manifest.libraries = getVersionTable().versions.get(getGameVersion().toString()).libraries;
        manifest.mainClass = env.equals("client") ? "zombie.gameStates.MainScreenState" : "zombie.network.Server";
        manifest.releaseTime = depotManifestDate.toString();
        manifest.time = OffsetDateTime.now(ZoneOffset.UTC).truncatedTo(ChronoUnit.SECONDS).toString();
        manifest.version = getGameVersion().toString();

        MAPPER.writeValue(f, manifest);
    }

    public static void generateVersionManifest(DepotManifest depot, Path out) throws IOException {
        LOGGER.info("Generating version manifest.");

        File launcherManifest = out.resolve(getGameVersion() + ".json").toFile();
        File versionManifest = out.resolve(VERSION_MANIFEST_JSON).toFile();

        String env = getEnvFromPlatformDir(out);
        String os = getOsFromPlatformDir(out);

        // Launcher manifest is guaranteed to exist by this point.
        // We can read it and calculate hash etc.
        byte[] bytes = Files.readAllBytes(launcherManifest.toPath());
        String sha1 = HEXFORMAT.formatHex(SHA1_DIGEST.digest(bytes));

        // Create dummy version entry (to be inserted later).
        VersionManifest.Version version = new VersionManifest.Version();
        version.id = getGameVersion().toString();
        version.url = "%s/%s/%s/%s.json".formatted(MANIFESTS_URL, env, os, getGameVersion().toString());
        version.sha1 = sha1;
        version.time = OffsetDateTime.now(ZoneOffset.UTC).truncatedTo(ChronoUnit.SECONDS).toString();
        version.releaseTime = depot.manifestDate;

        // Check for invalid data if the file exists and delete if found.
        if (versionManifest.exists()) {
            try {
                MAPPER.readValue(versionManifest, VersionManifest.class);
            } catch (DatabindException e) {
                LOGGER.warn("Existing version manifest could not be parsed. Deleting to overwrite.");
                if (!versionManifest.delete()) {
                    throw new RuntimeException("Failed to delete existing version manifest.");
                }
            }
        }

        // Add version if needed (if file already exists) or create a new one.
        if (versionManifest.exists()) {
            VersionManifest manifest = MAPPER.readValue(versionManifest, VersionManifest.class);

            String latestRelease = getLatestVersion().release;
            String latestUnstable = getLatestVersion().unstable;

            if (!Objects.equals(manifest.latest.release, latestRelease)) {
                manifest.latest.release = latestRelease;
            }

            if (!Objects.equals(manifest.latest.unstable, latestUnstable)) {
                manifest.latest.unstable = latestUnstable;
            }

            if (getGameVersion().isGreaterThan(manifest.versions.getFirst().id)) {
                manifest.versions.addFirst(version);
            } else if (getGameVersion().isLowerThan(manifest.versions.getLast().id)) {
                manifest.versions.addLast(version);
            } else {
                boolean old = false;
                for (VersionManifest.Version ver : manifest.versions) {
                    OffsetDateTime dummyDate = OffsetDateTime.parse(version.releaseTime);
                    OffsetDateTime compDate = OffsetDateTime.parse(ver.releaseTime);
                    if (ver.id.equals(getGameVersion().toString()) &&
                        (compDate.isBefore(dummyDate) || compDate.isEqual(dummyDate))) {
                        LOGGER.debug("Version found in manifest is the same but older depot. Updating.");

                        ver.id = version.id;
                        ver.releaseTime = version.releaseTime;
                        ver.sha1 = version.sha1;
                        ver.time = version.time;
                        ver.url = version.url;

                        old = true;
                    }
                }

                if (!old) {
                    LOGGER.info("Version already exists in version manifest.");
                    return;
                }
            }

            MAPPER.writeValue(versionManifest, manifest);
        } else {
            // New file, just write and finished!
            List<VersionManifest.Version> versions = List.of(version);

            VersionManifest manifest = new VersionManifest();
            manifest.latest = getLatestVersion();
            manifest.versions = versions;

            MAPPER.writeValue(versionManifest, manifest);
        }
    }

    public static VersionTable getVersionTable() {
        return versionTable;
    }

    public static String getEnvFromPlatformDir(Path dir) {
        return dir.getParent().getFileName().toString();
    }

    public static String getOsFromPlatformDir(Path dir) {
        return dir.getFileName().toString();
    }

    public static VersionManifest.LatestVersion getLatestVersion() {
        return latestVersion;
    }
}
