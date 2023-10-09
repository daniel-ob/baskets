document.addEventListener('DOMContentLoaded', function() {
    const inlineTitle = document.querySelector(".tabular h2");
    const inlineHelpText = document.createElement("div");
    inlineHelpText.style.padding = "10px";
    inlineHelpText.innerText = gettext('Please do not replace products: You can add new ones or delete existing ones');
    inlineTitle.insertAdjacentElement("afterend", inlineHelpText);
});
