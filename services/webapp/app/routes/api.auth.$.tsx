import type { LoaderFunctionArgs, ActionFunctionArgs } from '@remix-run/node'
import { useLoaderData, Form, useActionData } from '@remix-run/react'
import { auth, isCloudAuth } from '../auth/auth.server'

export async function loader({ params, request }: LoaderFunctionArgs) {
    // For PropelAuth (cloud), delegate to the provider
    if (isCloudAuth()) {
        return await auth.routes.loader(request, params)
    }

    // For local auth, check path and return appropriate data
    const url = new URL(request.url)
    const path = params['*'] || url.pathname.replace('/api/auth/', '')

    if (path === 'login') {
        // Check if user is already logged in
        const user = await auth.getUser(request)
        if (user) {
            return new Response(null, {
                status: 302,
                headers: { Location: '/' },
            })
        }
        return { action: 'login', mode: 'local' }
    }

    if (path === 'signup') {
        // Check if user is already logged in
        const user = await auth.getUser(request)
        if (user) {
            return new Response(null, {
                status: 302,
                headers: { Location: '/' },
            })
        }
        return { action: 'signup', mode: 'local' }
    }

    // For other routes (logout, etc), delegate to provider
    return await auth.routes.loader(request, params)
}

export async function action({ request, params }: ActionFunctionArgs) {
    return await auth.routes.action(request, params)
}

export default function Auth() {
    const data = useLoaderData<typeof loader>()
    const actionData = useActionData<{ error?: string }>()

    // If not local auth mode, render nothing
    if (!data || typeof data !== 'object' || !('mode' in data) || data.mode !== 'local') {
        return null
    }

    const isSignup = 'action' in data && data.action === 'signup'

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full space-y-8">
                <div>
                    <h1 className="text-center text-3xl font-bold text-gray-900 dark:text-white">
                        Chicory
                    </h1>
                    <h2 className="mt-6 text-center text-xl text-gray-600 dark:text-gray-300">
                        {isSignup ? 'Create your account' : 'Sign in to your account'}
                    </h2>
                </div>

                {actionData?.error && (
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
                        <p className="text-sm text-red-600 dark:text-red-400">{actionData.error}</p>
                    </div>
                )}

                <Form method="post" className="mt-8 space-y-6">
                    {isSignup && (
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label htmlFor="firstName" className="sr-only">First name</label>
                                <input
                                    id="firstName"
                                    name="firstName"
                                    type="text"
                                    autoComplete="given-name"
                                    className="appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white bg-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                    placeholder="First name"
                                />
                            </div>
                            <div>
                                <label htmlFor="lastName" className="sr-only">Last name</label>
                                <input
                                    id="lastName"
                                    name="lastName"
                                    type="text"
                                    autoComplete="family-name"
                                    className="appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white bg-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                    placeholder="Last name"
                                />
                            </div>
                        </div>
                    )}

                    <div className="rounded-md shadow-sm -space-y-px">
                        <div>
                            <label htmlFor="email" className="sr-only">Email address</label>
                            <input
                                id="email"
                                name="email"
                                type="email"
                                autoComplete="email"
                                required
                                className={`appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white bg-white dark:bg-gray-800 ${isSignup ? '' : 'rounded-t-md'} focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm`}
                                placeholder="Email address"
                            />
                        </div>
                        <div>
                            <label htmlFor="password" className="sr-only">Password</label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete={isSignup ? 'new-password' : 'current-password'}
                                required
                                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white bg-white dark:bg-gray-800 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                placeholder="Password"
                            />
                        </div>
                    </div>

                    <div>
                        <button
                            type="submit"
                            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                            {isSignup ? 'Create account' : 'Sign in'}
                        </button>
                    </div>
                </Form>

                <div className="text-center">
                    {isSignup ? (
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                            Already have an account?{' '}
                            <a href="/api/auth/login" className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
                                Sign in
                            </a>
                        </p>
                    ) : (
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                            Don't have an account?{' '}
                            <a href="/api/auth/signup" className="font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
                                Sign up
                            </a>
                        </p>
                    )}
                </div>
            </div>
        </div>
    )
}
