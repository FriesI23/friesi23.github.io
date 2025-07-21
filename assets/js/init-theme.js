// blog (c) by FriesI23
//
// blog is licensed under a
// Creative Commons Attribution-ShareAlike 4.0 International License.
//
// You should have received a copy of the license along with this
// work. If not, see <https://creativecommons.org/licenses/by-sa/4.0/>.

function onThemeChanged(theme) {
  // custom-footer.js
  setBackToTopOptions(theme);
  setGithubButton(theme);
  updateImages(theme);
}

function applyTheme(theme) {
  const node1 = document.getElementById("theme_source");
  const node2 = document.getElementById("theme_source_dark");

  if (theme === "dark") {
    node1.setAttribute("rel", "stylesheet alternate");
    node2.setAttribute("rel", "stylesheet");
  } else {
    node1.setAttribute("rel", "stylesheet");
    node2.setAttribute("rel", "stylesheet alternate");
  }
}

const themeDarkKey = "dark";
const themeLigthtKey = "light";

let theme = sessionStorage.getItem("theme");
if (!theme) {
  theme = window.matchMedia("(prefers-color-scheme: dark)").matches
    ? themeDarkKey
    : themeLigthtKey;
}
sessionStorage.setItem("theme", theme);
applyTheme(theme);

window
  .matchMedia("(prefers-color-scheme: dark)")
  .addEventListener("change", (e) => {
    const newTheme = e.matches ? themeDarkKey : themeLigthtKey;
    sessionStorage.setItem("theme", newTheme);
    applyTheme(newTheme);
  });

function updateImages(theme) {
  document.querySelectorAll(".theme-img").forEach((img) => {
    const newSrc = img.dataset[theme];
    if (newSrc && img.src !== newSrc) {
      img.src = newSrc;
    }
  });
}
