import { useState, useEffect } from 'react'
import './App.css'

interface AuditEvent {
  time: string;
  text: string;
  type: 'neutral' | 'action' | 'success';
}

interface MessageData {
  role: 'user' | 'assistant';
  content: string;
  action?: string;
  data?: any;
}

function App() {
  const [messages, setMessages] = useState<MessageData[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [auditLogs, setAuditLogs] = useState<AuditEvent[]>([])

  const addAuditLog = (text: string, type: 'neutral' | 'action' | 'success' = 'neutral') => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setAuditLogs(prev => [...prev, { time, text, type }]);
  }

  useEffect(() => {
    async function initSession() {
      try {
        const res = await fetch('http://localhost:8000/v1/sessions', { method: 'POST' })
        const data = await res.json()
        setSessionId(data.session_id)
        
        const shortId = data.session_id.substring(0,8);
        addAuditLog(`Session started: ${shortId}`, 'neutral');
        
        setMessages([{role: 'assistant', content: 'Hi! I can help you find something from Meera\'s Store. What are you looking for?'}])
      } catch (e) {
        console.error("Failed to init session", e)
      }
    }
    initSession()
  }, [])

  const handleActionMessage = async (msg: string) => {
    if (!sessionId) return;
    
    // We append user message to chat UI but without triggering input processing
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    addAuditLog(`User selected an action`, 'action');
    
    await executeChat(msg);
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId) return;
    const msg = input;
    setInput('')
    
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    addAuditLog(`User message received`, 'action');
    
    await executeChat(msg);
  }
  
  const executeChat = async (messageText: string) => {
    try {
      const res = await fetch(`http://localhost:8000/v1/chat/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText })
      })
      
      const data = await res.json()
      
      setMessages(prev => [...prev, {
        role: 'assistant', 
        content: data.content + (data.data?.payment_link_url ? `\n\nFallback Payment Link: ${data.data.payment_link_url}` : ''),
        action: data.action,
        data: data.data
      }])
      
      if (data.decision === "approved") {
         addAuditLog(`Action approved: ${data.action || 'chat'}`, 'success');
      } else if (data.decision === "gated_pending") {
         addAuditLog(`Action gated (pending confirmation)`, 'neutral');
      }
      
      // If we got an order back, open the native Razorpay modal popup
      if (data.data?.order_id && data.data?.razorpay_key_id) {
          addAuditLog(`Checkout initiated (${data.data.order_id})`, 'action');
          
          const options = {
              "key": data.data.razorpay_key_id,
              "amount": data.data.amount_paise,
              "currency": "INR",
              "name": "Growth Agent Store",
              "description": "Agent Checkout",
              "order_id": data.data.order_id,
              "handler": function (response: any) {
                  addAuditLog(`Payment successful: ${response.razorpay_payment_id}`, 'success');
                  setMessages(prev => [...prev, {
                      role: 'assistant', 
                      content: `Payment Successful! 🎉\nPayment ID: ${response.razorpay_payment_id}\n\nThe backend webhook is now securely recording this in the audit log.`
                  }]);
              },
              "theme": {
                  "color": "#1E1D1A"
              }
          };
          
          const rzp1 = new (window as any).Razorpay(options);
          rzp1.on('payment.failed', function (response: any){
              addAuditLog(`Payment failed: ${response.error.description}`, 'neutral');
              setMessages(prev => [...prev, {
                  role: 'assistant', 
                  content: `Payment failed or was cancelled. Error: ${response.error.description}`
              }]);
          });
          rzp1.open();
      }
      
    } catch (e) {
      setMessages(prev => [...prev, {role: 'assistant', content: 'Error communicating with server.'}])
      addAuditLog(`Error communicating with API`, 'neutral');
    }
  }

  return (
    <div className="dashboard-container">
      {/* Top Bar */}
      <div className="top-bar">
        <div className="top-bar-left">
          <h1>Agent Overview</h1>
          <p>Merchant Admin Dashboard</p>
        </div>
        <div className="top-bar-right">
          <button className="icon-btn">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
          </button>
          <button className="sign-out-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="main-grid">
        
        {/* LEFT: Ledger */}
        <div className="card">
          <div className="card-header">
            <h2><span className="dot"></span> Today's Ledger</h2>
          </div>
          <div className="ledger-stats">
            <div className="stat-row">
              <span>Sessions</span>
              <div className="stat-value">12</div>
            </div>
            <div className="stat-row">
              <span>Orders</span>
              <div className="stat-value">7</div>
            </div>
            <div className="revenue-box">
              <span>Revenue</span>
              <div className="rev-amount">₹8,940</div>
            </div>
          </div>
        </div>

        {/* CENTER: Chat */}
        <div className="card chat-card">
          <div className="card-header">
            <h2>Meera's Store Agent</h2>
          </div>
          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className="message-container">
                <div className={`message ${m.role}`}>
                  {m.content}
                </div>
                
                {/* Rich Product UI */}
                {m.action === 'search_catalog' && Array.isArray(m.data) && (
                  <div className="product-carousel">
                    {m.data.map((p, pIdx) => (
                      <div className="product-card" key={pIdx}>
                        <div className="img-placeholder">Image</div>
                        <h3>{p.title}</h3>
                        <p>₹{Math.floor(p.price_paise / 100)}</p>
                        <button onClick={() => handleActionMessage(`add ${p.sku} ${p.price_paise}`)}>Add</button>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Rich Cart UI */}
                {m.action === 'add_to_cart' && m.data && m.data.items && (
                  <div className="cart-card">
                    <h3>Confirm your order</h3>
                    {m.data.items.map((item: any, cIdx: number) => (
                      <div className="cart-item" key={cIdx}>
                        <span>{item.qty}× {item.title}</span>
                        <span>₹{Math.floor(item.price_paise / 100)}</span>
                      </div>
                    ))}
                    <div className="cart-total">
                      <span>Total</span>
                      <span>₹{Math.floor(m.data.total_paise / 100)}</span>
                    </div>
                    <button onClick={() => handleActionMessage(`checkout`)}>
                      Confirm & Pay 
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                    </button>
                  </div>
                )}
                
              </div>
            ))}
          </div>
          <div className="chat-input-wrapper">
            <input 
              value={input} 
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              placeholder="Type a message..." 
            />
            <button onClick={sendMessage}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>

        {/* RIGHT: Audit Log */}
        <div className="card">
          <div className="card-header">
            <div className="audit-header-content">
              <h2>Audit Log</h2>
              <div className="session-badge">{sessionId ? `sess_${sessionId.substring(0,4)}` : ''}</div>
            </div>
          </div>
          <div className="audit-timeline">
            {auditLogs.map((log, index) => (
              <div className="timeline-item" key={index}>
                <div className={`timeline-dot ${log.type}`}></div>
                <div className="timeline-content">
                  <div className="timeline-time">{log.time}</div>
                  <div className="timeline-text">{log.text}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}

export default App
