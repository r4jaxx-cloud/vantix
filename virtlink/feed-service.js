export function feedService(client,accounts){
  const unwrap=({data,error})=>{if(error)throw error;return data;};
  async function profile(){const row=await accounts.load();if(!row)throw new Error('Complete your profile first.');return row;}
  return {
    async list(){await profile();return unwrap(await client.rpc('virtlink_member_feed'));},
    async create(body){const text=String(body).trim();if(!text||text.length>2000)throw new Error('Write between 1 and 2,000 characters.');const row=await profile();return unwrap(await client.from('virtlink_posts').insert({author_id:row.user_id,body:text}).select('*').single());},
    async like(postId,liked){const row=await profile();if(liked)return unwrap(await client.from('virtlink_likes').upsert({post_id:postId,user_id:row.user_id},{onConflict:'post_id,user_id',ignoreDuplicates:true}));return unwrap(await client.from('virtlink_likes').delete().eq('post_id',postId).eq('user_id',row.user_id));},
    async comments(postId){await profile();const rows=unwrap(await client.from('virtlink_comments').select('*').eq('post_id',postId).order('created_at',{ascending:false}).order('id',{ascending:false}).limit(100));return rows.reverse();},
    async comment(postId,body){const text=String(body).trim();if(!text||text.length>1000)throw new Error('Write between 1 and 1,000 characters.');const row=await profile();return unwrap(await client.from('virtlink_comments').insert({post_id:postId,author_id:row.user_id,body:text}).select('*').single());},
    async removeComment(id){const row=await profile();return unwrap(await client.from('virtlink_comments').delete().eq('id',id).eq('author_id',row.user_id).select('id').single());},
    async remove(id){const row=await profile();return unwrap(await client.from('virtlink_posts').delete().eq('id',id).eq('author_id',row.user_id).select('id').single());}
  };
}
