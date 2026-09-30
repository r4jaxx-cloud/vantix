export function feedService(client,accounts){
  const unwrap=({data,error})=>{if(error)throw error;return data;};
  async function profile(){const row=await accounts.load();if(!row)throw new Error('Complete your profile first.');return row;}
  return {
    async list(){await profile();return unwrap(await client.from('virtlink_posts').select('*').order('created_at',{ascending:false}).order('id',{ascending:false}).limit(50));},
    async create(body){const text=String(body).trim();if(!text||text.length>2000)throw new Error('Write between 1 and 2,000 characters.');const row=await profile();return unwrap(await client.from('virtlink_posts').insert({author_id:row.user_id,body:text}).select('*').single());},
    async remove(id){const row=await profile();return unwrap(await client.from('virtlink_posts').delete().eq('id',id).eq('author_id',row.user_id).select('id').single());}
  };
}
