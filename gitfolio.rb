class Gitfolio < Formula
  include Language::Python::Virtualenv

  desc "Auto-generate ATS-friendly resume bullets from your GitHub commits"
  homepage "https://github.com/pranav-iiitdm/gitfolio"
  url "https://github.com/pranav-iiitdm/gitfolio/archive/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_SHA256_AFTER_RELEASE"
  license "MIT"

  depends_on "python@3.11"

  resource "click" do
    url "https://files.pythonhosted.org/packages/click-8.1.7.tar.gz"
    sha256 "REPLACE"
  end

  resource "PyGithub" do
    url "https://files.pythonhosted.org/packages/PyGithub-2.1.1.tar.gz"
    sha256 "REPLACE"
  end

  resource "anthropic" do
    url "https://files.pythonhosted.org/packages/anthropic-0.25.0.tar.gz"
    sha256 "REPLACE"
  end

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/PyYAML-6.0.1.tar.gz"
    sha256 "REPLACE"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/gitfolio", "--help"
  end
end
