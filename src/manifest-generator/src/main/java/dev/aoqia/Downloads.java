package net.aoqia;

import java.util.List;

public class Downloads {
    public List<Download> client;
    public List<Download> server;

    public static class Download {
        public String sha1;
        public Integer size;
        public String url;
    }
}
