// import { Link, useLocation } from 'react-router-dom';
// // import useAuth from '../hooks/useAuth';

// export default function Navbar() {
//   // const { user, logout } = useAuth();
//   const location = useLocation();

//   // Hide navbar in chat view
//   if (location.pathname === '/chat') return null;

//   return (
//     <nav className="navbar glass-effect">
//       <div className="nav-container">
//         <Link to="/" className="logo">
//           <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
//             <path d="M16 2L28 9V23L16 30L4 23V9L16 2Z" stroke="url(#navbarGradient)" strokeWidth="2" fill="none" />
//             <defs>
//               <linearGradient id="navbarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
//                 <stop offset="0%" style={{ stopColor: '#667EEA' }} />
//                 <stop offset="50%" style={{ stopColor: '#764BA2' }} />
//                 <stop offset="100%" style={{ stopColor: '#F093FB' }} />
//               </linearGradient>
//             </defs>

//           </svg>
//           <span>Tailor<strong>AI</strong></span>
//         </Link>
//         <div className="nav-links">
//           <Link to="/features">Features</Link>
//           <Link to="/about">About</Link>
//           {/* {user && <Link to="/chat" style={{ color: 'var(--accent)' }}>💬 Chat</Link>}
//           {user && (
//             <a href="#" onClick={(e) => { e.preventDefault(); logout(); }} style={{ color: 'var(--error)' }}>
//               🚪 Logout
//             </a>
//           )} */}
//         </div>
//       </div>
//     </nav>
//   );
// }


import { Link, useLocation } from 'react-router-dom';
// import useAuth from '../hooks/useAuth';

export default function Navbar() {
  // const { user, logout } = useAuth();
  const location = useLocation();

  // Hide navbar in chat view
  if (location.pathname === '/chat') return null;

  return (
    <nav className="navbar glass-effect">
      <div className="nav-container">
        <Link to="/" className="logo">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <path
              d="M16 2L28 9V23L16 30L4 23V9L16 2Z"
              stroke="url(#navbarGradient)"
              strokeWidth="2"
              fill="none"
            />
            <defs>
              <linearGradient id="navbarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{ stopColor: '#667EEA' }} />
                <stop offset="50%" style={{ stopColor: '#764BA2' }} />
                <stop offset="100%" style={{ stopColor: '#F093FB' }} />
              </linearGradient>
            </defs>
          </svg>
          <span>
            Tailor<strong>AI</strong>
          </span>
        </Link>

        <div className="nav-links">
          <Link to="/features">Features</Link>
          <Link to="/about">About</Link>

          {/* {user && <Link to="/chat" style={{ color: 'var(--accent)' }}>💬 Chat</Link>}
          {user && (
            <a href="#" onClick={(e) => { e.preventDefault(); logout(); }} style={{ color: 'var(--error)' }}>
              🚪 Logout
            </a>
          )} */}
        </div>
      </div>
    </nav>
  );
}

