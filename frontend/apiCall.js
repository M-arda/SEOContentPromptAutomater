function deasciifierNLowerer(str) {
        const charMap = {
            'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'İ': 'i', 'Ö': 'o', 'Ç': 'c', 'ı': 'i',
            'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'
        };

        return str
            .replace(/[\u00C0-\u017F]/g, ch => charMap[ch] || ch)
            .replace(/\s+/g, '') // remove all spaces (and tabs, newlines)
            .toLowerCase();
    }

export async function generate(brand, langs, model) {
    let brandDeasciified = deasciifierNLowerer(brand)
    const Inptopic = document.querySelector(`#${brandDeasciified}BaslikInp`).value;

    // Map content boxes for each language
    const contentBoxMap = {};
    const metaDescBoxMap = {};
    langs.forEach(lang => {
        const contentBox = document.querySelector(`#${brandDeasciified}${lang} .contentBox`);
        const metaDescBox = document.querySelector(`#${brandDeasciified}${lang} .metaDescBox`);
        if (contentBox) {
            contentBoxMap[lang] = contentBox;
        }
        if (metaDescBox) {
            metaDescBoxMap[lang] = metaDescBox;
        }
    });


    // Make the API request
    const res = await fetch("http://localhost:3169/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            brand: brand,
            topic: Inptopic,
            ai_model: model,
            langs: langs
        })
    });

    // Parse the API response
    const data = await res.json();
    console.log(data);

    // Update content boxes with the API response
    langs.forEach(lang => {
        const contentBox = contentBoxMap[lang];
        if (contentBox && data.content && data.content[lang]) {
            contentBox.textContent = data.introContent[lang].content; // Assumes API returns content per language
        }
    });

    let contents = data.contents;
    let metaDescs = data.metaDescs;
    let subTitles = data.subtitles;

    Object.keys(contents).forEach(langsContent => {
        contentBoxMap[langsContent].textContent = contents[langsContent];
    });

    Object.keys(metaDescs).forEach(langsDesc => {
        metaDescBoxMap[langsDesc].textContent = metaDescs[langsDesc];
    });

    console.log(subTitles);
}