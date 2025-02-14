package dev.aoqia;

import java.util.List;

public class VersionManifest {
    public LatestVersion latest;
    public List<Version> versions;

    public static class LatestVersion {
        public String release;
        public String unstable;

        public LatestVersion() {}

        /**
         * Constructs a LatestVersion object. Purposefully leaves one of the fields null.
         *
         * @param release The version to use.
         */
        public LatestVersion(String release) {
            if (release.contains("unstable")) {
                this.unstable = release;
            } else {
                this.release = release;
            }
        }
    }

    public static class Version {
        public String id;
        public String url;
        public String sha1;
        public String time;
        public String releaseTime;
    }
}
