package net.aoqia;

import java.util.HashMap;

public class AssetIndexManifest {
    public HashMap<String, AssetIndex> objects;

    public static class AssetIndex {
        public String hash;
        public String size;
    }
}
