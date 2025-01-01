package net.aoqia;

import java.util.List;
import java.util.Map;

public class VersionTable {
    public Map<String, Version> versions;

    public static class Version {
        public List<LauncherManifest.Library> libraries;
        public List<String> manifests;
    }
}
