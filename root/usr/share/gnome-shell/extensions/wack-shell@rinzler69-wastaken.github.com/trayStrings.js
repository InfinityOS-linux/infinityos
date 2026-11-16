import GLib from 'gi://GLib';

// Full labels rather than concatenated fragments, so word order is localizable.
// Locale variants fall back through GLib's ordered language preference list.
export const labels = {
    en: ['Hide', 'Show', 'Move to top bar', 'Move to menu', 'Application icons'],
    pl: ['Ukryj', 'Pokaż', 'Przenieś na górny pasek', 'Przenieś do menu', 'Ikony aplikacji'],
    de: ['Ausblenden', 'Anzeigen', 'In die obere Leiste verschieben', 'Ins Menü verschieben', 'Anwendungssymbole'],
    fr: ['Masquer', 'Afficher', 'Déplacer vers la barre supérieure', 'Déplacer vers le menu', 'Icônes des applications'],
    es: ['Ocultar', 'Mostrar', 'Mover a la barra superior', 'Mover al menú', 'Iconos de aplicaciones'],
    it: ['Nascondi', 'Mostra', 'Sposta nella barra superiore', 'Sposta nel menu', 'Icone delle applicazioni'],
    pt: ['Ocultar', 'Mostrar', 'Mover para a barra superior', 'Mover para o menu', 'Ícones de aplicações'],
    pt_BR: ['Ocultar', 'Mostrar', 'Mover para a barra superior', 'Mover para o menu', 'Ícones de aplicativos'],
    nl: ['Verbergen', 'Tonen', 'Naar de bovenbalk verplaatsen', 'Naar het menu verplaatsen', 'Toepassingspictogrammen'],
    cs: ['Skrýt', 'Zobrazit', 'Přesunout na horní panel', 'Přesunout do nabídky', 'Ikony aplikací'],
    sk: ['Skryť', 'Zobraziť', 'Presunúť na horný panel', 'Presunúť do ponuky', 'Ikony aplikácií'],
    uk: ['Приховати', 'Показати', 'Перемістити на верхню панель', 'Перемістити до меню', 'Піктограми програм'],
    ru: ['Скрыть', 'Показать', 'Переместить на верхнюю панель', 'Переместить в меню', 'Значки приложений'],
    be: ['Схаваць', 'Паказаць', 'Перамясціць на верхнюю панэль', 'Перамясціць у меню', 'Значкі праграм'],
    sv: ['Dölj', 'Visa', 'Flytta till överpanelen', 'Flytta till menyn', 'Programikoner'],
    da: ['Skjul', 'Vis', 'Flyt til toppanelet', 'Flyt til menuen', 'Programikoner'],
    nb: ['Skjul', 'Vis', 'Flytt til topplinjen', 'Flytt til menyen', 'Programikoner'],
    nn: ['Gøym', 'Vis', 'Flytt til topplinja', 'Flytt til menyen', 'Programikon'],
    fi: ['Piilota', 'Näytä', 'Siirrä yläpalkkiin', 'Siirrä valikkoon', 'Sovelluskuvakkeet'],
    no: ['Skjul', 'Vis', 'Flytt til topplinjen', 'Flytt til menyen', 'Programikoner'],
    fur: ['Plate', 'Mostre', 'Sposte te sbare superiôr', 'Sposte tal menù', 'Iconis des aplicazions'],
    oc: ['Amagar', 'Afichar', 'Desplaçar cap a la barra superiora', 'Desplaçar cap al menú', 'Icònas de las aplicacions'],
    is: ['Fela', 'Sýna', 'Færa á efstu stikuna', 'Færa í valmynd', 'Forritatákn'],
    et: ['Peida', 'Näita', 'Liiguta ülaribale', 'Liiguta menüüsse', 'Rakenduste ikoonid'],
    lv: ['Paslēpt', 'Rādīt', 'Pārvietot uz augšējo joslu', 'Pārvietot uz izvēlni', 'Lietotņu ikonas'],
    lt: ['Slėpti', 'Rodyti', 'Perkelti į viršutinę juostą', 'Perkelti į meniu', 'Programų piktogramos'],
    hu: ['Elrejtés', 'Megjelenítés', 'Áthelyezés a felső sávra', 'Áthelyezés a menübe', 'Alkalmazásikonok'],
    ro: ['Ascunde', 'Arată', 'Mută în bara de sus', 'Mută în meniu', 'Pictogramele aplicațiilor'],
    bg: ['Скриване', 'Показване', 'Преместване в горната лента', 'Преместване в менюто', 'Икони на приложения'],
    sr: ['Сакриј', 'Прикажи', 'Премести на горњу траку', 'Премести у мени', 'Иконе програма'],
    'sr@latin': ['Sakrij', 'Prikaži', 'Premesti na gornju traku', 'Premesti u meni', 'Ikone programa'],
    hr: ['Sakrij', 'Prikaži', 'Premjesti na gornju traku', 'Premjesti u izbornik', 'Ikone aplikacija'],
    bs: ['Sakrij', 'Prikaži', 'Premjesti na gornju traku', 'Premjesti u meni', 'Ikone aplikacija'],
    sl: ['Skrij', 'Pokaži', 'Premakni v zgornjo vrstico', 'Premakni v meni', 'Ikone programov'],
    mk: ['Сокриј', 'Прикажи', 'Премести во горната лента', 'Премести во менито', 'Икони на апликации'],
    sq: ['Fshih', 'Shfaq', 'Zhvendos te shiriti i sipërm', 'Zhvendos te menyja', 'Ikonat e aplikacioneve'],
    el: ['Απόκρυψη', 'Εμφάνιση', 'Μετακίνηση στην επάνω γραμμή', 'Μετακίνηση στο μενού', 'Εικονίδια εφαρμογών'],
    tr: ['Gizle', 'Göster', 'Üst çubuğa taşı', 'Menüye taşı', 'Uygulama simgeleri'],
    ca: ['Amaga', 'Mostra', 'Mou a la barra superior', 'Mou al menú', 'Icones de les aplicacions'],
    eu: ['Ezkutatu', 'Erakutsi', 'Eraman goiko barrara', 'Eraman menura', 'Aplikazioen ikonoak'],
    gl: ['Agochar', 'Amosar', 'Mover á barra superior', 'Mover ao menú', 'Iconas das aplicacións'],
    ar: ['إخفاء', 'إظهار', 'نقل إلى الشريط العلوي', 'نقل إلى القائمة', 'أيقونات التطبيقات'],
    he: ['הסתרה', 'הצגה', 'העברה לסרגל העליון', 'העברה לתפריט', 'סמלי יישומים'],
    fa: ['پنهان کردن', 'نمایش', 'انتقال به نوار بالا', 'انتقال به منو', 'نمادهای برنامه‌ها'],
    ur: ['چھپائیں', 'دکھائیں', 'اوپری بار میں منتقل کریں', 'مینو میں منتقل کریں', 'ایپس کے آئیکن'],
    hi: ['छिपाएँ', 'दिखाएँ', 'ऊपरी पट्टी पर ले जाएँ', 'मेन्यू में ले जाएँ', 'ऐप के चिह्न'],
    bn: ['লুকান', 'দেখান', 'উপরের বারে সরান', 'মেনুতে সরান', 'অ্যাপের আইকন'],
    pa: ['ਓਹਲੇ ਕਰੋ', 'ਦਿਖਾਓ', 'ਉੱਪਰਲੀ ਪੱਟੀ ਵਿੱਚ ਭੇਜੋ', 'ਮੇਨੂ ਵਿੱਚ ਭੇਜੋ', 'ਐਪਾਂ ਦੇ ਆਈਕਾਨ'],
    gu: ['છુપાવો', 'બતાવો', 'ઉપરની પટ્ટીમાં ખસેડો', 'મેનુમાં ખસેડો', 'એપ્લિકેશનનાં ચિહ્નો'],
    mr: ['लपवा', 'दाखवा', 'वरच्या पट्टीवर हलवा', 'मेनूमध्ये हलवा', 'ॲपची चिन्हे'],
    ta: ['மறை', 'காட்டு', 'மேல் பட்டைக்கு நகர்த்து', 'பட்டிக்கு நகர்த்து', 'செயலி சின்னங்கள்'],
    te: ['దాచు', 'చూపు', 'పై పట్టీకి తరలించు', 'మెనూకు తరలించు', 'అనువర్తన చిహ్నాలు'],
    kn: ['ಮರೆಮಾಡಿ', 'ತೋರಿಸಿ', 'ಮೇಲಿನ ಪಟ್ಟಿಗೆ ಸರಿಸಿ', 'ಮೆನುಗೆ ಸರಿಸಿ', 'ಅನ್ವಯಗಳ ಚಿಹ್ನೆಗಳು'],
    ml: ['മറയ്ക്കുക', 'കാണിക്കുക', 'മുകളിലെ ബാറിലേക്ക് നീക്കുക', 'മെനുവിലേക്ക് നീക്കുക', 'ആപ്ലിക്കേഷൻ ചിഹ്നങ്ങൾ'],
    ne: ['लुकाउनुहोस्', 'देखाउनुहोस्', 'माथिल्लो पट्टीमा सार्नुहोस्', 'मेनुमा सार्नुहोस्', 'एपका प्रतिमाहरू'],
    si: ['සඟවන්න', 'පෙන්වන්න', 'ඉහළ තීරුවට ගෙනයන්න', 'මෙනුවට ගෙනයන්න', 'යෙදුම් නිරූපක'],
    th: ['ซ่อน', 'แสดง', 'ย้ายไปที่แถบด้านบน', 'ย้ายไปที่เมนู', 'ไอคอนแอปพลิเคชัน'],
    vi: ['Ẩn', 'Hiện', 'Chuyển lên thanh trên cùng', 'Chuyển vào trình đơn', 'Biểu tượng ứng dụng'],
    id: ['Sembunyikan', 'Tampilkan', 'Pindahkan ke bilah atas', 'Pindahkan ke menu', 'Ikon aplikasi'],
    ms: ['Sembunyikan', 'Paparkan', 'Alih ke bar atas', 'Alih ke menu', 'Ikon aplikasi'],
    fil: ['Itago', 'Ipakita', 'Ilipat sa itaas na bar', 'Ilipat sa menu', 'Mga icon ng app'],
    ja: ['非表示', '表示', 'トップバーに移動', 'メニューに移動', 'アプリのアイコン'],
    ko: ['숨기기', '표시', '상단 표시줄로 이동', '메뉴로 이동', '앱 아이콘'],
    zh: ['隐藏', '显示', '移到顶栏', '移到菜单', '应用图标'],
    zh_TW: ['隱藏', '顯示', '移至頂端列', '移至選單', '應用程式圖示'],
    zh_HK: ['隱藏', '顯示', '移至頂端列', '移至選單', '應用程式圖示'],
    ka: ['დამალვა', 'ჩვენება', 'ზედა ზოლში გადატანა', 'მენიუში გადატანა', 'აპლიკაციების ხატულები'],
    hy: ['Թաքցնել', 'Ցուցադրել', 'Տեղափոխել վերին վահանակ', 'Տեղափոխել ընտրացանկ', 'Հավելվածների պատկերակներ'],
    az: ['Gizlət', 'Göstər', 'Üst panelə köçür', 'Menyuya köçür', 'Tətbiq nişanları'],
    kk: ['Жасыру', 'Көрсету', 'Жоғарғы панельге жылжыту', 'Мәзірге жылжыту', 'Қолданба таңбашалары'],
    uz: ['Yashirish', 'Ko‘rsatish', 'Yuqori panelga ko‘chirish', 'Menyuga ko‘chirish', 'Ilova belgilari'],
    mn: ['Нуух', 'Харуулах', 'Дээд самбар руу зөөх', 'Цэс рүү зөөх', 'Аппын дүрсүүд'],
    af: ['Versteek', 'Wys', 'Skuif na boonste balk', 'Skuif na kieslys', 'Toepassingsikone'],
    sw: ['Ficha', 'Onyesha', 'Hamisha hadi upau wa juu', 'Hamisha hadi menyu', 'Aikoni za programu'],
    eo: ['Kaŝi', 'Montri', 'Movi al la supra breto', 'Movi al la menuo', 'Aplikaĵaj piktogramoj'],
    ga: ['Folaigh', 'Taispeáin', 'Bog go dtí an barra uachtarach', 'Bog go dtí an roghchlár', 'Deilbhíní feidhmchlár'],
    cy: ['Cuddio', 'Dangos', 'Symud i’r bar uchaf', 'Symud i’r ddewislen', 'Eiconau rhaglenni'],
};

export function trayText(key, languages = GLib.get_language_names()) {
    const index = ['hide', 'show', 'panel', 'menu', 'manage'].indexOf(key);
    for (const locale of languages) {
        const normalized = locale.replace(/\.[^@]+/, '');
        const language = normalized.split(/[_@-]/)[0];
        const modifier = normalized.includes('@') ? normalized.split('@')[1] : null;
        const values = labels[normalized] ?? labels[`${language}@${modifier}`] ?? labels[language];
        if (values)
            return values[index];
    }
    return labels.en[index];
}
