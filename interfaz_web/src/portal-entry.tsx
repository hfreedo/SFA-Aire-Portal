import {createRoot} from 'react-dom/client';
import RemoteWorkspace from './RemoteWorkspace';
import InvitationScreen from './features/access/InvitationScreen';
import './style.css';
const invitation=location.pathname.startsWith('/invitacion')||new URLSearchParams(location.hash.slice(1)).has('invitacion');
createRoot(document.getElementById('root')!).render(invitation?<InvitationScreen/>:<RemoteWorkspace/>);
