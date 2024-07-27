import IndexHtml from './index.html';

export default {
	async fetch(request, env, ctx) {
		// verify path
		const path = (new URL(request.url)).pathname
		console.log(path);
		if (!/^\/(.*?)\/(\d*)$/.test(path)) {
			return new Response('Not Found', { status: 404 });
		}
		// get the video ID from the path
		const videoId = path.substring(1);
		if (!videoId) {
			return new Response('Not Found', { status: 404 });
		}
		
		// read data.html from local file system
		const data = new Response(IndexHtml);
		const html = await data.text();
		
		const replaced = html.replace('{{VIDID}}', "v/"+videoId);

		return new Response(replaced, {
			headers: {
				'content-type': 'text/html',
			},
		});
	},
};
