import React, { useState } from 'react';
import SessionTimeline from './components/SessionTimeline';
import EmbeddedChat from './components/EmbeddedChat';
import AuthScreen from './components/AuthScreen';
import { auth } from './firebase';
import { signOut } from 'firebase/auth';

function App() {
  const [globalAuthUser, setGlobalAuthUser] = useState<string | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<any[]>([
    { time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'}), desc: 'Session started: sess_a1b2', type: 'info' }
  ]);

  const addTimelineEvent = (event: any) => {
    setTimelineEvents(prev => [...prev, { time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'}), ...event }]);
  };

  if (!globalAuthUser) {
    return <AuthScreen onAuthSuccess={(user) => setGlobalAuthUser(user)} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-paper to-[#EAE8E1] text-ink p-4 md:p-8 font-body selection:bg-ledger-blue/20">
      
      {/* 3D Floating Header */}
      <header className="max-w-7xl mx-auto mb-8 relative z-10">
        <div className="absolute inset-0 bg-white/40 backdrop-blur-md rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] -z-10 transform -skew-x-2"></div>
        <div className="p-6 border border-ink-faint/10 rounded-2xl bg-white/60 backdrop-blur-xl shadow-sm transition-all duration-300 hover:shadow-md">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-display text-3xl md:text-4xl font-semibold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-ink to-ledger-blue">
                Agent Overview
              </h1>
              <p className="text-ink-faint mt-1 font-medium tracking-wide uppercase text-sm">Merchant Admin Dashboard</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden md:flex h-12 w-12 rounded-full bg-ledger-blue/10 items-center justify-center shadow-inner border border-ledger-blue/20">
                <svg className="w-6 h-6 text-ledger-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <button 
                onClick={async () => {
                  try {
                    await signOut(auth);
                    setGlobalAuthUser(null);
                  } catch (error) {
                    console.error('Error signing out', error);
                  }
                }}
                className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 font-medium rounded-lg shadow-sm transition-all text-sm"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-12 gap-6 relative z-10">
        
        {/* Left Column: Stats (3 cols) */}
        <div className="col-span-12 md:col-span-3 space-y-6">
          {/* 3D Stat Card */}
          <div className="group relative rounded-2xl transition-all duration-300 hover:-translate-y-2 hover:shadow-[0_20px_40px_rgba(43,69,112,0.1)] bg-white border border-ink-faint/10 p-6 shadow-sm overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-ledger-blue/5 rounded-full blur-3xl -mr-10 -mt-10 transition-transform group-hover:scale-150"></div>
            
            <h2 className="font-display text-xl mb-6 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-ledger-amber animate-pulse"></span>
              Today's Ledger
            </h2>
            
            <ul className="space-y-4">
              <li className="flex justify-between items-center p-3 rounded-lg hover:bg-paper transition-colors cursor-default">
                <span className="font-medium text-ink/80 text-sm">Sessions</span>
                <span className="money text-lg font-semibold bg-white px-3 py-1 rounded shadow-sm border border-ink-faint/10">12</span>
              </li>
              <li className="flex justify-between items-center p-3 rounded-lg hover:bg-paper transition-colors cursor-default">
                <span className="font-medium text-ink/80 text-sm">Orders</span>
                <span className="money text-lg font-semibold bg-white px-3 py-1 rounded shadow-sm border border-ink-faint/10">7</span>
              </li>
              <li className="flex justify-between items-center p-3 rounded-lg bg-ledger-blue/5 border border-ledger-blue/10 transform transition-transform hover:scale-105 shadow-sm">
                <span className="font-semibold text-ledger-blue text-sm">Revenue</span>
                <span className="money text-lg font-bold text-ledger-blue">₹8,940</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Middle Column: Chatbot (5 cols) */}
        <div className="col-span-12 md:col-span-5 h-[600px]">
          <EmbeddedChat onTimelineUpdate={addTimelineEvent} globalUser={globalAuthUser} />
        </div>

        {/* Right Column: Session Timeline (4 cols) */}
        <div className="col-span-12 md:col-span-4 h-[600px] overflow-hidden flex flex-col">
          <div className="bg-white rounded-2xl p-6 border border-ink-faint/10 shadow-sm relative flex-1 flex flex-col overflow-hidden">
            {/* Subtle paper texture/gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-paper/30 pointer-events-none"></div>
            
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-ink-faint/10 relative z-10 shrink-0">
              <h2 className="font-display text-xl">Audit Log</h2>
              <span className="money bg-ink text-paper px-3 py-1 rounded-md text-xs shadow-md">sess_a1b2</span>
            </div>
            
            <div className="relative z-10 flex-1 overflow-y-auto pr-2">
              <SessionTimeline events={timelineEvents} />
            </div>
          </div>
        </div>
      </main>

    </div>
  );
}

export default App;


