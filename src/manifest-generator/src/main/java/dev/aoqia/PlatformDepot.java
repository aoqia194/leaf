package dev.aoqia;

public enum PlatformDepot {
    MAC_CLIENT(108602),
    LINUX_CLIENT(108603),
    WIN_CLIENT(108604),
    COMMON_SERVER(380871),
    MAC_SERVER(380872),
    LINUX_SERVER(380873),
    WIN_SERVER(380874);

    private final int depotId;

    PlatformDepot(int depotId) {
        this.depotId = depotId;
    }

    public int getDepotId() {
        return depotId;
    }
}
