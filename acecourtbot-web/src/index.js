import IndexHtml from './index.html';

const fileMap = {
	'/Igiari.woff': { file: await import('./igiari.woff'), type: 'font/woff' },
	'/courtbg.png': { file: await import('./courtbg.png'), type: 'image/png' },
	'/favicon/favicon.ico': { file: await import('./favicon/favicon.ico'), type: 'image/x-icon' },
	'/favicon/android-chrome-192x192.png': { file: await import('./favicon/android-chrome-192x192.png'), type: 'image/png' },
	'/favicon/android-chrome-512x512.png': { file: await import('./favicon/android-chrome-512x512.png'), type: 'image/png' },
	'/favicon/apple-touch-icon.png': { file: await import('./favicon/apple-touch-icon.png'), type: 'image/png' },
	'/favicon/site.webmanifest': { file: await import('./favicon/site.webmanifest'), type: 'application/json' },
};

export default {
	async fetch(request, env, ctx) {
		// verify path
		const path = (new URL(request.url)).pathname

        const fileInfo = fileMap[path];
        if (fileInfo) {
            return new Response(fileInfo.file.default, {
                headers: {
                    'content-type': fileInfo.type,
                },
            });
        }

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
		
		const replaced = html.replace(/{{VIDID}}/g, "v/"+videoId);

		return new Response(replaced, {
			headers: {
				'content-type': 'text/html',
			},
		});
	},
};
