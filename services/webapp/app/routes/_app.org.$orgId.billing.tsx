import React from "react";
import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { useLoaderData } from "@remix-run/react";
import { auth } from "~/auth/auth.server";
import { CreditCardIcon, ReceiptRefundIcon, CheckCircleIcon, XCircleIcon } from "@heroicons/react/24/outline";

interface LoaderData {
  orgName: string;
  currentPlan: string;
  billingCycle: string;
  nextBillingDate: string;
  isActive: boolean;
}

export async function loader({ params, request }: LoaderFunctionArgs) {
  const orgId = params.orgId;
  if (!orgId) {
    throw new Response("Organization ID is required", { status: 400 });
  }

  // Verify user is authenticated and has access to this org
  const user = await auth.getUser(request, {});
  if (!user || !user.orgIdToUserOrgInfo || !user.orgIdToUserOrgInfo[orgId]) {
    throw new Response("Unauthorized", { status: 403 });
  }

  // In a real app, you'd fetch billing information from your billing provider
  // This is placeholder data
  return json({
    orgName: user.orgIdToUserOrgInfo[orgId].orgName,
    currentPlan: "Free Plan",
    billingCycle: "Monthly",
    nextBillingDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toLocaleDateString(),
    isActive: true
  });
}

export default function OrganizationBilling() {
  const { currentPlan, billingCycle, nextBillingDate, isActive } = useLoaderData<typeof loader>();

  // Available plans
  const plans = [
    {
      name: "Free Plan",
      price: "$0",
      features: [
        "Up to 3 team members",
        "Basic analytics",
        "1 active project",
        "Community support"
      ],
      isCurrent: currentPlan === "Free Plan"
    },
    {
      name: "Pro Plan",
      price: "$29",
      features: [
        "Up to 10 team members",
        "Advanced analytics",
        "Unlimited projects",
        "Priority support"
      ],
      isCurrent: currentPlan === "Pro Plan"
    },
    {
      name: "Enterprise Plan",
      price: "$99",
      features: [
        "Unlimited team members",
        "Custom analytics",
        "Unlimited projects",
        "Dedicated support",
        "Custom integrations"
      ],
      isCurrent: currentPlan === "Enterprise Plan"
    }
  ];

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
        Billing & Plans
      </h2>
      
      {/* Current Subscription */}
      <div className="bg-white dark:bg-gray-800 shadow-sm rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-8">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Current Subscription</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Plan</p>
            <p className="font-medium text-gray-900 dark:text-white">{currentPlan}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Billing Cycle</p>
            <p className="font-medium text-gray-900 dark:text-white">{billingCycle}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Next Billing Date</p>
            <p className="font-medium text-gray-900 dark:text-white">{nextBillingDate}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Status</p>
            <p className="font-medium text-gray-900 dark:text-white flex items-center">
              {isActive ? (
                <>
                  <CheckCircleIcon className="h-5 w-5 text-green-500 mr-1" />
                  Active
                </>
              ) : (
                <>
                  <XCircleIcon className="h-5 w-5 text-red-500 mr-1" />
                  Inactive
                </>
              )}
            </p>
          </div>
        </div>
      </div>
      
      {/* Payment Methods */}
      <div className="bg-white dark:bg-gray-800 shadow-sm rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-8">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Payment Methods</h3>
          <button className="text-sm text-purple-600 hover:text-purple-800 dark:text-purple-400 dark:hover:text-purple-300 font-medium">
            Add Payment Method
          </button>
        </div>
        <div className="flex items-center p-3 border border-gray-200 dark:border-gray-700 rounded-md">
          <CreditCardIcon className="h-8 w-8 text-gray-400 mr-3" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">No payment methods added</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Add a credit card to upgrade your plan</p>
          </div>
        </div>
      </div>
      
      {/* Available Plans */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Available Plans</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div 
              key={plan.name}
              className={`bg-white dark:bg-gray-800 shadow-sm rounded-lg border ${
                plan.isCurrent 
                  ? 'border-purple-500 dark:border-purple-400 ring-2 ring-purple-500 dark:ring-purple-400' 
                  : 'border-gray-200 dark:border-gray-700'
              } p-4`}
            >
              <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">{plan.name}</h4>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mb-4">{plan.price}<span className="text-sm font-normal text-gray-500 dark:text-gray-400">/month</span></p>
              <ul className="space-y-2 mb-6">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-start">
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                    <span className="text-sm text-gray-600 dark:text-gray-300">{feature}</span>
                  </li>
                ))}
              </ul>
              <button
                className={`w-full py-2 px-4 rounded-md font-medium ${
                  plan.isCurrent
                    ? 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200 cursor-default'
                    : 'bg-purple-600 text-white hover:bg-purple-700 dark:bg-purple-700 dark:hover:bg-purple-600'
                }`}
                disabled={plan.isCurrent}
              >
                {plan.isCurrent ? 'Current Plan' : 'Upgrade'}
              </button>
            </div>
          ))}
        </div>
      </div>
      
      {/* Billing History */}
      <div className="mt-8">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Billing History</h3>
          <button className="text-sm text-purple-600 hover:text-purple-800 dark:text-purple-400 dark:hover:text-purple-300 font-medium flex items-center">
            <ReceiptRefundIcon className="h-4 w-4 mr-1" />
            Download All
          </button>
        </div>
        <div className="bg-white dark:bg-gray-800 shadow-sm rounded-lg border border-gray-200 dark:border-gray-700 p-6 text-center">
          <p className="text-gray-500 dark:text-gray-400">No billing history available</p>
        </div>
      </div>
    </div>
  );
}
