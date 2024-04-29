// blog (c) by FriesI23
//
// blog is licensed under a
// Creative Commons Attribution-ShareAlike 4.0 International License.
//
// You should have received a copy of the license along with this
// work. If not, see <https://creativecommons.org/licenses/by-sa/4.0/>.

var theme = sessionStorage.getItem("theme");
if (!theme) {
  if (
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  ) {
    theme = "dark";
  } else {
    theme = "light";
  }
}
if (theme === "dark") {
  sessionStorage.setItem("theme", "dark");
  node1 = document.getElementById("theme_source");
  node2 = document.getElementById("theme_source_dark");
  node1.setAttribute("rel", "stylesheet alternate");
  node2.setAttribute("rel", "stylesheet");
} else {
  sessionStorage.setItem("theme", "light");
}
