import { useMemo, useState } from "react";

const samples = {
  en_fake: "BREAKING: You won't believe this miracle cure. Secret government lab confirms it works overnight.",
  en_real: "Reuters reports that regional leaders met today to discuss food security and drought response.",
  fr_fake: "INCROYABLE: ce vaccin tue, ne ratez pas cette révélation choquante.",
  fr_real: "France 24 rapporte un accord régional sur la sécurité alimentaire signé ce matin."
};

const translations = {
  en: {
    title: "DeepScan AI",
    tagline: "See the truth. Share with confidence.",
    inputType: "Input type",
    content: "Content",
    analyze: "Analyze",
    analyzing: "Analyzing...",
    verdict: "Verdict",
    score: "Reliability Score",
    explanation: "Explanation",
    modules: "Module Breakdown",
    sample: "Load sample",
    typeText: "Text",
    typeUrl: "URL",
    typeImage: "Image",
    typeVideo: "Video",
    paste: "Paste text or URL here",
    upload: "Upload file",
    clear: "Clear"
  },
  fr: {
    title: "DeepScan AI",
    tagline: "See the truth. Share with confidence.",
    inputType: "Type d'entrée",
    content: "Contenu",
    analyze: "Analyser",
    analyzing: "Analyse en cours...",
    verdict: "Verdict",
    score: "Score de fiabilité",
    explanation: "Explication",
    modules: "Détails des modules",
    sample: "Charger un exemple",
    typeText: "Texte",
    typeUrl: "URL",
    typeImage: "Image",
    typeVideo: "Vidéo",
    paste: "Collez le texte ou l'URL ici",
    upload: "Importer un fichier",
    clear: "Effacer"
  }
};

const verdictStyles = {
  Reliable: "bg-aurora/20 text-aurora border-aurora",
  Fiable: "bg-aurora/20 text-aurora border-aurora",
  Doubtful: "bg-amber-500/20 text-amber-300 border-amber-400",
  Douteux: "bg-amber-500/20 text-amber-300 border-amber-400",
  Fake: "bg-ember/20 text-ember border-ember",
  Faux: "bg-ember/20 text-ember border-ember"
};

const formatSignals = (key, signals) => {
  if (!signals || typeof signals !== "object") return "-";

  const lines = [];

  if (signals.provider) {
    lines.push(`Provider: ${signals.provider}${signals.model ? ` (${signals.model})` : ""}`);
  }

  if (key === "nlp") {
    const emotional = signals.emotional_words?.length ? signals.emotional_words.join(", ") : "none";
    const clickbait = signals.clickbait_patterns?.length ? signals.clickbait_patterns.join(", ") : "none";
    const bias = signals.bias_words?.length ? signals.bias_words.join(", ") : "none";
    lines.push(`Emotional words: ${emotional}.`);
    lines.push(`Clickbait patterns: ${clickbait}.`);
    lines.push(`Bias/absolute words: ${bias}.`);
  }

  if (key === "source") {
    lines.push(`Domain: ${signals.domain || "-"}.`);
    lines.push(`HTTPS: ${signals.https ? "yes" : "no"}.`);
    if (signals.shortener !== undefined) {
      lines.push(`Shortener: ${signals.shortener ? "yes" : "no"}.`);
    }
    if (signals.punycode !== undefined) {
      lines.push(`Punycode: ${signals.punycode ? "yes" : "no"}.`);
    }
    if (signals.ip_domain !== undefined) {
      lines.push(`IP domain: ${signals.ip_domain ? "yes" : "no"}.`);
    }
    if (signals.suspicious_keywords) {
      const sk = signals.suspicious_keywords.length ? signals.suspicious_keywords.join(", ") : "none";
      lines.push(`Suspicious keywords: ${sk}.`);
    }
    if (signals.reputation) {
      lines.push(`Trusted list: ${signals.reputation.trusted ? "yes" : "no"}.`);
      lines.push(`Suspicious list: ${signals.reputation.suspicious ? "yes" : "no"}.`);
      if (signals.reputation.press_rank_score !== undefined) {
        lines.push(`Press rank score: ${signals.reputation.press_rank_score}.`);
      }
    }
    if (signals.whois) {
      lines.push(`WHOIS enabled: ${signals.whois.enabled ? "yes" : "no"}.`);
      if (signals.whois.age_days !== null && signals.whois.age_days !== undefined) {
        lines.push(`Domain age: ${signals.whois.age_days} days.`);
      }
    }
  }

  if (key === "fact_check") {
    lines.push(`Status: ${signals.status || "-"}.`);
    if (signals.match) {
      lines.push(`Matched claim: ${signals.match}.`);
    }
  }

  if (key === "image" || key === "deepfake") {
    const flags = signals.flags?.length ? signals.flags.join(", ") : "none";
    lines.push(`Flags: ${flags}.`);
  }

  if (key === "evidence") {
    if (signals.status) {
      lines.push(`Status: ${signals.status}.`);
    }
    if (signals.provider) {
      lines.push(`Provider: ${signals.provider}.`);
    }
    if (signals.matches?.length) {
      const sourceList = signals.matches
        .slice(0, 3)
        .map((m) => `${m.title} (${m.domain})`)
        .join("; ");
      lines.push(`Sources: ${sourceList}.`);
    }
  }

  if (!lines.length) {
    return JSON.stringify(signals);
  }
  return lines.join(" ");
};

export default function App() {
  const [lang, setLang] = useState("fr");
  const [type, setType] = useState("text");
  const [content, setContent] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const t = translations[lang];

  const progressValue = useMemo(() => {
    if (!result) return 0;
    return result.score || 0;
  }, [result]);

  const handleAnalyze = async () => {
    if (!content.trim()) return;
    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, content })
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({
        verdict: "Error",
        score: 0,
        explanation: "Backend not reachable. Please start the API.",
        modules: {}
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFile = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result?.toString() || "";
      setContent(base64);
    };
    reader.readAsDataURL(file);
  };

  const loadSample = (key) => {
    setContent(samples[key]);
    setType("text");
  };

  return (
    <div className="min-h-screen px-4 py-10 md:px-10">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <p className="text-sky text-sm uppercase tracking-[0.3em]">{t.title}</p>
            <h1 className="text-4xl md:text-5xl font-display font-semibold mt-3">{t.tagline}</h1>
            <p className="text-slate-300 mt-4 max-w-xl">
              Detect fake news, deepfakes, and misleading sources in seconds. Built for low-bandwidth,
              mobile-first environments.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              className={`px-3 py-2 rounded-full text-sm ${lang === "fr" ? "bg-sky text-white" : "bg-white/10"}`}
              onClick={() => setLang("fr")}
            >
              FR
            </button>
            <button
              className={`px-3 py-2 rounded-full text-sm ${lang === "en" ? "bg-sky text-white" : "bg-white/10"}`}
              onClick={() => setLang("en")}
            >
              EN
            </button>
          </div>
        </div>

        <div className="grid lg:grid-cols-[1.2fr_0.8fr] gap-8 mt-10">
          <div className="glass rounded-3xl p-6 md:p-8">
            <div className="flex flex-wrap items-center gap-3">
              <span className="badge bg-white/10 text-white">{t.inputType}</span>
              {["text", "url", "image", "video"].map((item) => (
                <button
                  key={item}
                  onClick={() => setType(item)}
                  className={`px-3 py-2 rounded-full text-sm ${
                    type === item ? "bg-aurora text-night" : "bg-white/10 text-white"
                  }`}
                >
                  {t[`type${item.charAt(0).toUpperCase() + item.slice(1)}`]}
                </button>
              ))}
              <button className="ml-auto text-sm text-slate-300" onClick={() => setContent("")}>{t.clear}</button>
            </div>

            <div className="mt-6">
              <label className="text-sm text-slate-300">{t.content}</label>
              <textarea
                className="w-full mt-2 min-h-[180px] rounded-2xl bg-white/5 border border-white/10 p-4 text-white"
                placeholder={t.paste}
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
              {(type === "image" || type === "video") && (
                <div className="mt-3">
                  <label className="text-sm text-slate-300">{t.upload}</label>
                  <input
                    type="file"
                    className="mt-2 block w-full text-sm"
                    onChange={handleFile}
                  />
                </div>
              )}
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                onClick={handleAnalyze}
                className="px-6 py-3 rounded-full bg-aurora text-night font-semibold"
              >
                {loading ? t.analyzing : t.analyze}
              </button>
              <button
                onClick={() => loadSample(lang === "fr" ? "fr_fake" : "en_fake")}
                className="px-4 py-2 rounded-full bg-white/10 text-white text-sm"
              >
                {t.sample} (Fake)
              </button>
              <button
                onClick={() => loadSample(lang === "fr" ? "fr_real" : "en_real")}
                className="px-4 py-2 rounded-full bg-white/10 text-white text-sm"
              >
                {t.sample} (Real)
              </button>
            </div>
          </div>

          <div className="glass rounded-3xl p-6 md:p-8">
            <h2 className="font-display text-2xl">{t.score}</h2>
            <div className="mt-6 flex items-center gap-6">
              <div className="progress-ring" style={{ "--value": progressValue }}>
                <div>{result ? Math.round(progressValue * 100) : 0}%</div>
              </div>
              <div>
                <p className="text-slate-300 text-sm">{t.verdict}</p>
                <div
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-semibold mt-2 ${
                    verdictStyles[result?.verdict] || "bg-white/10 text-white border-white/10"
                  }`}
                >
                  {result?.verdict || "-"}
                </div>
                <p className="text-slate-300 text-sm mt-4">Language: {result?.language || "-"}</p>
              </div>
            </div>

            <div className="mt-8">
              <h3 className="font-display text-xl">{t.explanation}</h3>
              <p className="text-slate-300 mt-3 text-sm leading-relaxed">
                {result?.explanation || "-"}
              </p>
            </div>
          </div>
        </div>

        <div className="glass rounded-3xl p-6 md:p-8 mt-8">
          <h2 className="font-display text-2xl">{t.modules}</h2>
          <div className="grid md:grid-cols-2 gap-6 mt-6">
            {result?.modules
              ? Object.entries(result.modules).map(([key, module]) => (
                  <div key={key} className="bg-white/5 border border-white/10 rounded-2xl p-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-display text-lg capitalize">{key.replace("_", " ")}</h4>
                      <span className="text-slate-300 text-sm">{Math.round(module.score * 100)}%</span>
                    </div>
                    <p className="text-slate-300 text-sm mt-2">{module.explanation}</p>
                    <p className="text-xs text-slate-400 mt-3 whitespace-pre-wrap">
                      {formatSignals(key, module.signals)}
                    </p>
                  </div>
                ))
              : "-"}
          </div>
        </div>
      </div>
    </div>
  );
}
