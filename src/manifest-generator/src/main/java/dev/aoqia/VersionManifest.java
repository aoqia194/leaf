package dev.aoqia;

import java.util.List;

public class VersionManifest {
    public LatestVersion latest;
    public List<Version> versions;

    public static class LatestVersion {
        public String release;
        public String unstable;
    }

    public static class Version {
        public String id;
        public String url;
        public String sha1;
        public String time;
        public String releaseTime;
    }
}
