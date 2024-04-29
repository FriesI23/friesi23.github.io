// blog (c) by FriesI23
//
// blog is licensed under a
// Creative Commons Attribution-ShareAlike 4.0 International License.
//
// You should have received a copy of the license along with this
// work. If not, see <https://creativecommons.org/licenses/by-sa/4.0/>.

$(function () {
  $(".theme__toggle").on("click", function () {
    node1 = document.getElementById("theme_source");
    node2 = document.getElementById("theme_source_dark");
    if (node1.getAttribute("rel") == "stylesheet") {
      node1.setAttribute("rel", "stylesheet alternate");
      node2.setAttribute("rel", "stylesheet");
      sessionStorage.setItem("theme", "dark");
      setBackToTopOptions("dark");
    } else {
      node2.setAttribute("rel", "stylesheet alternate");
      node1.setAttribute("rel", "stylesheet");
      sessionStorage.setItem("theme", "light");
      setBackToTopOptions("light");
    }
    return false;
  });
});
