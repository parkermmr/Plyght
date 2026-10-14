/*
Boots swagger-ui from a file instead of an inline script, so the page
works under a script-src 'self' policy. The spec and redirect urls ride
data attributes on this script tag.
*/
(function () {
  var tag = document.currentScript;
  window.ui = SwaggerUIBundle({
    url: tag.dataset.spec,
    dom_id: "#swagger-ui",
    layout: "BaseLayout",
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true,
    oauth2RedirectUrl: window.location.origin + tag.dataset.redirect,
    presets: [
      SwaggerUIBundle.presets.apis,
      SwaggerUIBundle.SwaggerUIStandalonePreset,
    ],
  });
})();
