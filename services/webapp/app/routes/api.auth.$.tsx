import type { LoaderFunctionArgs } from '@remix-run/node'
import { auth } from '../auth/auth.server'

export async function loader({ params, request }: LoaderFunctionArgs) {
    return await auth.routes.loader(request, params)
}

export default function Auth() {
    return null
}

export async function action({ request, params }: LoaderFunctionArgs) {
    return await auth.routes.action(request, params)
}
