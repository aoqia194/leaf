package net.aoqia;

import java.util.HashMap;

public class DepotManifest {
    public String depotId;
    public String manifestId;
    public String manifestDate;
    public String numFiles;
    public String numChunks;
    public String bytesDisk;
    public String bytesCompressed;
    public HashMap<String, Entry> entries;

    public static class Entry {
        public String size;
        public String chunks;
        public String sha1;
        public String flags;
    }
}
