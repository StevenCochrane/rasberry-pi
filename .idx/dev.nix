{ pkgs, ... }: {
  # Choose the software channel
  channel = "stable-24.05";

  # Install system packages (Python, Pip, etc.)
  packages = [
    pkgs.python311
    pkgs.python311Packages.pip
  ];

  # Install editor extensions automatically
  idx.extensions = [
    "ms-python.python"
    "ms-python.vscode-pylance"
  ];

  # Run commands when the workspace is first created
  idx.workspace.onCreate = {
    install-deps = "pip install -r requirements.txt";
  };
}