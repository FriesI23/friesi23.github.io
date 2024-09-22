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
  var colorScheme = "";
  if (theme === "light") {
    colorScheme = "no-preference: light; light: light; dark: light;";
  } else {
    colorScheme = "no-preference: dark; light: dark; dark: dark;";
  }

  let elements = document.getElementsByClassName("github-button");
  for (var i = 0; i < elements.length; i++) {
    let e = elements[i];
    e.setAttribute("data-color-scheme", colorScheme);
  }

  function reloadGitHubButtonsScript() {
    let script = document.createElement("script");
    script.src = "https://buttons.github.io/buttons.js";
    script.async = true;
    script.defer = true;

    let existingScript = document.querySelector(
      'script[src="https://buttons.github.io/buttons.js"]'
    );
    if (existingScript) {
      existingScript.parentNode.replaceChild(script, existingScript);
    } else {
      document.body.appendChild(script);
    }
  }

  reloadGitHubButtonsScript();
}

$(function () {
  let currentTheme = sessionStorage.getItem("theme");
  onThemeChanged(currentTheme);
});
