package dev.aoqia;

import java.util.HashMap;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;

public class LauncherManifest {
    public Args arguments;
    public AssetIndex assetIndex;
    public JavaVersion javaVersion;
    public List<Library> libraries;
    public String mainClass;
    public String releaseTime;
    public String time;
    public String version;

    public static class Library {
        public String name;
        @JsonInclude(JsonInclude.Include.NON_NULL)
        public List<Rule> rules;

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
            public List<Rule> rules;
            // Object can be List<String> or String.
            public Object value;
        }
    }

    public static class Rule {
        public String action;
        @JsonInclude(JsonInclude.Include.NON_NULL)
        public List<HashMap<String, Boolean>> features;
        @JsonInclude(JsonInclude.Include.NON_NULL)
        public RuleArgOs os;

        public static class RuleArgOs {
            // Platform architecture.
            @JsonInclude(JsonInclude.Include.NON_NULL)
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
