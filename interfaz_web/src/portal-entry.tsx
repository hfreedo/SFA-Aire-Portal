import {createRoot} from 'react-dom/client';
import './style.css';
import RemoteWorkspace from './RemoteWorkspace';
import InvitationScreen from './features/access/InvitationScreen';
import PortalBoundary from './shared/PortalBoundary';
const invitation=location.pathname.startsWith('/invitacion')||new URLSearchParams(location.hash.slice(1)).has('invitacion');
createRoot(document.getElementById('root')!).render(<PortalBoundary>{invitation?<InvitationScreen/>:<RemoteWorkspace/>}</PortalBoundary>);
