export async function generate(brand, model) {
    // Get the topic from the input field
    const topic = document.querySelector(`#${brand}BaslikInp`).value;

    // Get all elements with IDs starting with the brand
    const allSections = document.querySelectorAll(`[id^="${brand}"]`);

    // Define valid languages (you can adjust this list based on your needs)
    const validLanguages = ['turkce', 'ingilizce', "rusca", "arapca", "ispanyolca", "fransizca", "almanca"]; // Add more languages if needed

    // Filter to get only language-specific sections
    const langSections = Array.from(allSections).filter(section => {
        const lang = section.id.replace(brand, '');
        return validLanguages.includes(lang);
    });

    // Extract languages from the filtered sections
    const langs = langSections.map(section => section.id.replace(brand, ''));

    // Map content boxes for each language
    const contentBoxMap = {};
    const metaDescBoxMap = {};
    langs.forEach(lang => {
        const contentBox = document.querySelector(`#${brand}${lang} .contentBox`);
        const metaDescBox = document.querySelector(`#${brand}${lang} .metaDescBox`);
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
            topic: topic,
            model: model,
            langs: langs
        })
    });

    // Parse the API response
    const data = await res.json();
    console.log(data);

    // Update content boxes with the API response
    // langs.forEach(lang => {
    //     const contentBox = contentBoxMap[lang];
    //     if (contentBox && data.introContent && data.introContent[lang]) {
    //         contentBox.textContent = data.introContent[lang].content; // Assumes API returns content per language
    //     }
    // });

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