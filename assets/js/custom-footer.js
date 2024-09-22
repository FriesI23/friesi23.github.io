function onThemeChanged(theme) {
  setBackToTopOptions(theme);
  setGithubButton(theme);
}

function setBackToTopOptions(theme) {
  var options = { diameter: 60 };

  if (theme === "light") {
    options.backgroundColor = "rgb(255, 82, 82)";
    options.textColor = "#fff";
  } else {
    options.backgroundColor = "#ddd";
    options.textColor = "#000";
  }

  let backToTopElement = document.getElementById("back-to-top");
  if (backToTopElement && backToTopElement.parentNode) {
    backToTopElement.parentNode.removeChild(backToTopElement);
    let styleElements = document.getElementsByTagName("style");
    for (var i = 0; i < styleElements.length; i++) {
      let styleElement = styleElements[i];
      let styleContent = styleElement.textContent || styleElement.innerText;
      let b2t = styleContent.indexOf("#back-to-top");
      if (b2t !== -1 && styleElement.parentNode) {
        styleElement.parentNode.removeChild(styleElement);
      }
    }
  }
  addBackToTop(options);
}

function setGithubButton(theme) {
  if (theme === "light") {
    var showId = "gh-button-container-light";
    var hideId = "gh-button-container-dark";
  } else {
    var showId = "gh-button-container-dark";
    var hideId = "gh-button-container-light";
  }
  var showElement = document.getElementById(showId);
  var hideElement = document.getElementById(hideId);
  if (showElement) {
    showElement.style.display = "flex";
  }
  if (hideElement) {
    hideElement.style.display = "none";
  }
}

$(function () {
  let currentTheme = sessionStorage.getItem("theme");
  onThemeChanged(currentTheme);
});
