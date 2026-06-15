// blog (c) by FriesI23
//
// blog is licensed under a
// Creative Commons Attribution-ShareAlike 4.0 International License.
//
// You should have received a copy of the license along with this
// work. If not, see <https://creativecommons.org/licenses/by-sa/4.0/>.

(function () {
  document.querySelectorAll(".prompts-copy-btn").forEach(function (btn) {
    var text = btn.dataset.copyText;
    if (!text) return;
    var original = btn.textContent;
    btn.addEventListener("click", function () {
      navigator.clipboard.writeText(text).then(function () {
        btn.textContent = "✅ 已复制";
        setTimeout(function () {
          btn.textContent = original;
        }, 1500);
      });
    });
  });
})();
