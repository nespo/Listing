// static/admin/js/footer_widget.js

document.addEventListener('DOMContentLoaded', function() {
    function toggleFields() {
        var widgetType = document.getElementById('id_widget_type').value;
        var textField = document.getElementById('id_text').parentElement.parentElement;
        var textFieldDescription = document.getElementById('id_text');
        var htmlField = document.getElementById('id_custom_html').parentElement.parentElement;
        var htmlFieldCode = document.getElementById('id_custom_html');
        var linksGroup = document.getElementById('links-group');

        if (widgetType === 'logo_text') {
            textField.style.display = '';
            textFieldDescription.style.display = '';
            htmlField.style.display = 'none';
            linksGroup.style.display = 'none';
        } else if (widgetType === 'link1' || widgetType === 'link2') {
            textField.style.display = 'none';
            htmlField.style.display = 'none';
            linksGroup.style.display = '';
        } else if (widgetType === 'html') {
            textField.style.display = 'none';
            htmlField.style.display = '';
            htmlFieldCode.style.display = '';
            linksGroup.style.display = 'none';
        } else {
            textField.style.display = 'none';
            htmlField.style.display = 'none';
            linksGroup.style.display = 'none';
        }
    }

    var widgetTypeField = document.getElementById('id_widget_type');
    widgetTypeField.addEventListener('change', toggleFields);
    toggleFields();
});
