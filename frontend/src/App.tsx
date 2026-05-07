import React, { useState, useEffect } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import { 
  Languages, 
  AudioLines, 
  PenTool, 
  MoonStar, 
  SunMedium, 
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Home
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

import OCRPage from "./features/ocr/OCRPage";
import TranscribePage from "./features/transcribe/TranscribePage";
import KanjiPage from "./features/kanji/KanjiPage";

const HomePage = () => (
  <div className="p-8">
    <div className="max-w-4xl">
      <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-slate-900">
        <Sparkles size={16} />
        Welcome to OnisLanguage Unified AI
      </div>
      <h1 className="text-4xl font-bold mb-4">Master Japanese with AI-Powered Tools</h1>
      <p className="text-xl text-slate-600 dark:text-slate-400 mb-8">
        A consolidated platform for OCR, Transcription, and Kanji Recognition.
      </p>
      <div className="grid gap-6 md:grid-cols-3">
        {[
          { icon: Languages, title: "OCR", desc: "Extract Japanese text from images.", link: "/ocr" },
          { icon: AudioLines, title: "Transcribe", desc: "Convert audio/video to text.", link: "/transcribe" },
          { icon: PenTool, title: "Kanji", desc: "Recognize handwritten Kanji.", link: "/kanji" },
        ].map((tool) => (
          <Link 
            key={tool.title} 
            to={tool.link}
            className="p-6 rounded-3xl border border-slate-200 bg-white shadow-soft hover:border-sky-500 transition-all dark:border-slate-800 dark:bg-slate-900/50"
          >
            <tool.icon className="mb-4 text-sky-500" size={32} />
            <h3 className="text-lg font-semibold mb-2">{tool.title}</h3>
            <p className="text-sm text-slate-500">{tool.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  </div>
);

const SidebarItem = ({ to, icon: Icon, label, collapsed }: { to: string, icon: any, label: string, collapsed: boolean }) => {
  const location = useLocation();
  const active = location.pathname === to;

  return (
    <Link
      to={to}
      className={cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-2xl transition-all duration-200",
        active 
          ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-lg" 
          : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
      )}
    >
      <Icon size={22} className="shrink-0" />
      {!collapsed && <span className="font-medium">{label}</span>}
    </Link>
  );
};

function App() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 transition-colors dark:bg-slate-950 dark:text-white">
      {/* Sidebar */}
      <aside 
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-slate-200 bg-white/80 backdrop-blur-xl transition-all duration-300 dark:border-slate-800 dark:bg-slate-900/80",
          collapsed ? "w-20" : "w-64"
        )}
      >
        <div className="flex h-20 items-center px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-500 text-white shadow-lg shadow-sky-500/20">
              <Sparkles size={22} />
            </div>
            {!collapsed && <span className="text-xl font-bold tracking-tight">Onis AI</span>}
          </div>
        </div>

        <nav className="flex-1 space-y-2 p-4">
          <SidebarItem to="/" icon={Home} label="Dashboard" collapsed={collapsed} />
          <div className="my-4 h-px bg-slate-100 dark:bg-slate-800" />
          <SidebarItem to="/ocr" icon={Languages} label="Image to Text" collapsed={collapsed} />
          <SidebarItem to="/transcribe" icon={AudioLines} label="Transcription" collapsed={collapsed} />
          <SidebarItem to="/kanji" icon={PenTool} label="Kanji Recognition" collapsed={collapsed} />
        </nav>

        <div className="p-4 space-y-2">
          <button
            onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}
            className="flex w-full items-center gap-3 rounded-2xl p-3 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
          >
            {theme === "dark" ? <SunMedium size={22} /> : <MoonStar size={22} />}
            {!collapsed && <span className="font-medium">{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>}
          </button>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex w-full items-center gap-3 rounded-2xl p-3 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
          >
            {collapsed ? <ChevronRight size={22} /> : <ChevronLeft size={22} />}
            {!collapsed && <span className="font-medium">Collapse Sidebar</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className={cn(
        "flex-1 transition-all duration-300",
        collapsed ? "ml-20" : "ml-64"
      )}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/ocr" element={<OCRPage />} />
          <Route path="/transcribe" element={<TranscribePage />} />
          <Route path="/kanji" element={<KanjiPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
