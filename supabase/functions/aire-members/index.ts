import {handleMembers} from "./core.ts";
Deno.serve((req:Request)=>handleMembers(req,{url:Deno.env.get("SUPABASE_URL")||"",publicKey:Deno.env.get("SUPABASE_ANON_KEY")||"",secret:Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||""}));
