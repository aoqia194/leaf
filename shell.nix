{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python314
    uv
    hatch
    depotdownloader
    temurin-bin-25
  ];

  env.UV_PYTHON = "${pkgs.python314}/bin/python3.14";
}
