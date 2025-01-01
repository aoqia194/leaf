package net.aoqia;

import java.util.HashMap;
import java.util.List;

public class LauncherManifest {
    public Args arguments;
    public AssetIndex assetIndex;
    public JavaVersion javaVersion;
    public List<Library> libraries = List.of();
    public String mainClass;
    public String releaseTime;
    public String time;
    public String version;

    public static class Library {
        public String name;
        // Object is Rule here, but it fills with null all over, so I am too lazy to fix it.
        public List<Object> rules = List.of();

        public static class Artifact {
            public String path;
            public String sha1;
            public Integer size;
            public String url;
        }
    }

    public static class Args {
        // Object can be String or RuleArg.
        public List<Object> game = List.of();
        public List<Object> jvm = List.of();

        public static class RuleArg {
            public List<Rule> rules = List.of();
            // Object can be List<String> or String.
            public Object value;
        }
    }

    public static class Rule {
        public String action;
        public List<HashMap<String, Boolean>> features = List.of();
        public RuleArgOs os;

        public static class RuleArgOs {
            // Platform architecture.
            public String arch;
            // Platform short name (windows, osx)
            public String name;
        }
    }

    public static class AssetIndex {
        public String sha1;
        public Integer size;
        public String url;
    }
}
