document.addEventListener('DOMContentLoaded', function() {
    const inlineTitle = document.querySelector(".tabular h2");
    const inlineHelpText = document.createElement("div");
    inlineHelpText.style.padding = "10px";
    inlineHelpText.innerText = "Veuillez ne pas remplacer des produits : " +
        "Vous pouvez en ajouter des nouveaux et supprimer les existants";
    inlineTitle.insertAdjacentElement("afterend", inlineHelpText);
});
