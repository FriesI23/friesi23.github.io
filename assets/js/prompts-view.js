// blog (c) by FriesI23
//
// blog is licensed under a
// Creative Commons Attribution-ShareAlike 4.0 International License.
//
// You should have received a copy of the license along with this
// work. If not, see <https://creativecommons.org/licenses/by-sa/4.0/>.

(function () {
  var KEY = "prompts-view";
  var saved = localStorage.getItem(KEY);
  if (saved) {
    var input = document.getElementById("prompts-view-" + saved);
    if (input) input.checked = true;
  }
  document.querySelectorAll('input[name="prompts-view"]').forEach(function (input) {
    input.addEventListener("change", function () {
      if (input.checked) localStorage.setItem(KEY, input.value);
    });
  });
})();
