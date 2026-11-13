import json
import os
from pathlib import Path
from typing import Any, Dict, List
from playwright.sync_api import Page
from rich.console import Console

console = Console()


class FormDiscovery:
    def __init__(self, page: Page):
        self.page = page

    def discover(self) -> Dict[str, Any]:
        console.print("[cyan]Discovering form fields from current page...[/]")

        # Extract CAS form elements while excluding w3 masthead search bar
        discovery_script = """
        () => {
            const results = [];
            
            // 1. Locate CAS main form (usually form[name="formBean"] or form[action*="actvReport"])
            let form = document.querySelector('form[name*="formBean"]') || 
                       document.querySelector('form[action*="actvReport"]') || 
                       document.querySelector('form[action*="cas"]') ||
                       document.querySelector('#ibm-content form');

            let elements = [];
            if (form) {
                elements = Array.from(form.querySelectorAll('input, select, textarea'));
            } else {
                // Find all forms excluding ibm-search-form
                const allForms = Array.from(document.querySelectorAll('form')).filter(f => {
                    const fid = (f.id || '').toLowerCase();
                    const fname = (f.name || '').toLowerCase();
                    return !fid.includes('ibm-search') && !fid.includes('masthead') && !fname.includes('search');
                });
                
                if (allForms.length > 0) {
                    allForms.forEach(f => {
                        elements.push(...Array.from(f.querySelectorAll('input, select, textarea')));
                    });
                } else {
                    const mainArea = document.querySelector('#ibm-content, main, .ibm-container') || document.body;
                    elements = Array.from(mainArea.querySelectorAll('input, select, textarea')).filter(el => {
                        return !el.closest('#ibm-masthead, #ibm-universal-nav, #ibm-search-form, header, footer');
                    });
                }
            }

            elements.forEach((el) => {
                const tag = el.tagName.toLowerCase();
                const type = (el.getAttribute('type') || (tag === 'select' ? 'select' : tag === 'textarea' ? 'textarea' : 'text')).toLowerCase();
                const name = el.getAttribute('name') || '';
                const id = el.getAttribute('id') || '';

                if (type === 'hidden' || type === 'submit' || type === 'button' || type === 'reset' || type === 'password') {
                    return;
                }

                // Ignore IBM top bar search input (q / qt)
                if (name === 'qt' || id === 'q' || id.includes('ibm-search')) {
                    return;
                }

                // Find human-readable label
                let label = '';
                if (id) {
                    const labelEl = document.querySelector(`label[for="${id}"]`);
                    if (labelEl) label = labelEl.innerText.trim();
                }
                if (!label) {
                    // Check previous table cell or container
                    let parentTd = el.closest('td');
                    if (parentTd) {
                        let prevTd = parentTd.previousElementSibling;
                        if (prevTd) {
                            label = prevTd.innerText.trim();
                        }
                    }
                }
                if (!label) {
                    let parent = el.closest('div, p');
                    if (parent) {
                        const clone = parent.cloneNode(true);
                        clone.querySelectorAll('input, select, textarea').forEach(child => child.remove());
                        label = clone.innerText.trim();
                    }
                }
                if (!label) {
                    label = name || id;
                }

                // Clean label
                label = label.replace(/[\\*\\:\\n\\r]/g, '').trim();

                const isRequired = el.hasAttribute('required') || el.classList.contains('required') || (label && label.includes('*'));
                const maxLength = el.getAttribute('maxlength') ? parseInt(el.getAttribute('maxlength')) : (name.includes('actyDesc') ? 70 : null);

                let options = [];
                if (tag === 'select') {
                    el.querySelectorAll('option').forEach(opt => {
                        const val = opt.getAttribute('value') !== null ? opt.getAttribute('value') : opt.innerText;
                        const text = opt.innerText.trim();
                        if (val !== '' && text !== '-- Select --' && text !== 'Please Select' && text !== '') {
                            options.push({ value: val, label: text, text: text });
                        }
                    });
                }

                results.push({
                    field_id: id || name,
                    name: name,
                    label: label,
                    field_type: tag === 'select' ? 'select' : tag === 'textarea' ? 'textarea' : type,
                    tag: tag,
                    type: type,
                    required: isRequired,
                    max_length: maxLength,
                    options: options,
                    default_value: el.value || ''
                });
            });

            return {
                version: "1.0.0",
                url: window.location.href,
                title: document.title,
                count: results.length,
                fields: results
            };
        }
        """

        metadata = self.page.evaluate(discovery_script)
        console.print(f"[green]Discovered {len(metadata.get('fields', []))} interactive fields from CAS form![/]")
        return metadata

    def save_metadata(self, metadata: Dict[str, Any], output_path: str = "artifacts/discovered_fields.json"):
        path = Path(output_path)
        os.makedirs(path.parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Saved discovered metadata to:[/] {output_path}")
