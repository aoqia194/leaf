use indoc::indoc;

pub(crate) const TEST_DEPOT_MANIFEST: &str = indoc! {r#"
Content Manifest for Depot 108602 

Manifest ID / date     : 7984161633207534069 / 12/17/2024 17:50:27 
Total number of files  : 51436 
Total number of chunks : 45197 
Total bytes on disk    : 11307127538 
Total bytes compressed : 5642932592 


Size Chunks File SHA                                 Flags Name
   0      0 0000000000000000000000000000000000000000    40 Project Zomboid.app
   0      0 0000000000000000000000000000000000000000    40 Project Zomboid.app\Contents
1700      1 5f77da0bcbf6a8a5571d85030b3cdf002d21da1e     0 Project Zomboid.app\Contents\Info.plist
   0      0 0000000000000000000000000000000000000000    40 Project Zomboid.app\Contents\Java
   0      0 0000000000000000000000000000000000000000    40 Project Zomboid.app\Contents\Java\.lwjgl
   0      0 0000000000000000000000000000000000000000    40 Project Zomboid.app\Contents\Java\astar
 605      1 8823fc239f12d3d508b18a98ec30f33e838da3f3     0 Project Zomboid.app\Contents\Java\astar\ASearchNode.class
 707      1 b3afc1558091ef28726fb983773fc948950c5847     0 Project Zomboid.app\Contents\Java\astar\AStar$SearchNodeComparator.class
3462      1 b85eb699446f796ec61827b77bcd7a9f49a400dc     0 Project Zomboid.app\Contents\Java\astar\AStar.class
"#};

pub(crate) const TEST_VERSION_TABLE: &str = indoc! {r#"
{
  "versions": {
    "42.0.0-unstable.25057": {
      "inherits": "41.78.16",
      "manifests": [
        7984161633207534069,
        5804831784883836119,
        884533456349664449
      ]
    },
    "41.78.16": {
      "arguments": {
        "game": [],
        "jvm": [
          "-Djava.awt.headless=true",
          {
            "rules": [
              {
                "action": "allow",
                "os": {
                  "name": "windows"
                }
              }
            ],
            "value": "-Djava.library.path=./win64/;./"
          },
          {
            "rules": [
              {
                "action": "allow",
                "os": {
                  "name": "linux"
                }
              }
            ],
            "value": [
              "-Djava.library.path=./linux64/;./",
              "-Djava.security.egd=file:/dev/./urandom"
            ]
          }
        ]
      },
      "mainClass": {
        "client": "zombie.gameStates.MainScreenState",
        "server": "zombie.network.Server"
      },
      "manifests": [
        2540194756181522692,
        1153657949707515857,
        6286577881064486829
      ]
    }
  }
}
"#};
