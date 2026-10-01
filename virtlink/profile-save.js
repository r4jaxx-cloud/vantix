// Discard results from work started under a previous account/session state.
export function profileSaver({save,revision,publish,result}) {
  let busy=false;
  return async input=>{
    if(busy)return;
    busy=true;const started=revision();
    try {
      const row=await save(input);
      if(started!==revision())return;
      publish(row);result({saved:true});
    } catch(error) {
      if(started!==revision())return;
      const message=error.code==='23505'?'That username is already taken. Choose another.':error.code==='42501'?'Your session needs checking. Open Account settings and sign in again.':'Could not save. Your changes are still here. Check your connection and try again.';
      result({error:message});
    } finally {busy=false;}
  };
}
