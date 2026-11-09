class Apex < Formula
  desc "Autonomous self-healing code engine: CEGIS 1-token synthesis, 663k probes/sec fuzzer, Linux kernel engine (pip = 0)"
  homepage "https://github.com/raghavkhandal72-coder/apex"
  url "https://github.com/raghavkhandal72-coder/apex/releases/download/v0.9.0/apex.pyz"
  sha256 "6abb38663a349469854d689aefe66e86da54b9267ccbc8ab59c38c793ed3fc4d"
  license "MIT"
  version "0.9.0"

  depends_on "python@3.11"

  def install
    bin.install "apex.pyz" => "apex"
  end

  test do
    system "#{bin}/apex", "--version"
    system "#{bin}/apex", "linux", "syscall", "read"
  end
end
