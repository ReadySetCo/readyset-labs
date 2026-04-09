import { Outlet, Link, useLocation } from 'react-router-dom';
import { Sparkles, LayoutDashboard, Lightbulb } from 'lucide-react';

export default function Layout() {
  const location = useLocation();
  
  return (
    <div className="min-h-screen gradient-bg">
      {/* Header */}
      <header className="border-b border-slate-800/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-xl gradient-accent flex items-center justify-center group-hover:animate-pulse-glow transition-all">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-display font-bold text-white">Brand Intelligence</h1>
                <p className="text-xs text-slate-500">Creative Dimensions Scraper</p>
              </div>
            </Link>
            
            <nav className="flex items-center gap-2">
              <Link 
                to="/"
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  location.pathname === '/' 
                    ? 'bg-indigo-500/20 text-indigo-300' 
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span className="text-sm font-medium">Dashboard</span>
              </Link>
              <Link 
                to="/idea-bank"
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  location.pathname === '/idea-bank' 
                    ? 'bg-yellow-500/20 text-yellow-300' 
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <Lightbulb className="w-4 h-4" />
                <span className="text-sm font-medium">Idea Bank</span>
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <p className="text-center text-sm text-slate-600">
            Brand Intelligence Scraper • Powered by GPT-5.1 + Firecrawl + Apify
          </p>
        </div>
      </footer>
    </div>
  );
}

