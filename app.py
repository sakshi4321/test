from flask import Flask,render_template,request
from sim_with_seed import sim
import pickle
import os
import csv
import numpy as np
import matplotlib.pyplot as plt

app = Flask(__name__)
@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response
@app.route('/', methods=['GET', 'POST'])

def form():
    if request.method == 'POST':
        dsoc= int(request.form["dsoc"])
        #print(dsoc)
        csoc = int(request.form["csoc"])
        #print(csoc)
        timereq=int(request.form["Charging time in minutes"])
        policies_gen(csoc/100,dsoc/100,timereq)
        for i in range(1,5):
            closed_loop_opt(i)

    return render_template('index.html')
#level
def policies_gen(SOCo,SOC_desired,Time_by_user,capacity):
    C1 = [3.6, 4.0, 4.4, 4.8, 5.2, 5.6, 6.0, 7.0, 8.0]
    C2 = [3.6, 4.0, 4.4, 4.8, 5.2, 5.6, 6.0, 7.0]
    C3 = [3.6, 4.0, 4.4, 4.8, 5.2, 5.6]

    C4_LIMITS = [0.1, 4.81]

    DIR = 'data'
    FILENAME ='all'

    ##############################################################################

    # 16 % energy loss assumed 
    def integrand(x, a):
        return a*x

    Crated=capacity
    avg_current=(SOC_desired-SOCo)*capacity*5/(4*Time_by_user)

    ####################################################33

    # Pre-initialize arrays and counters
    policies = -1.*np.ones((1000,4));
    valid_policies = -1.*np.ones((1000,4));

    count = valid_count = 0
    count_policies=0

    # Generate policies
    for c1, c2, c3 in [(c1,c2,c3) for c1 in C1 for c2 in C2 for c3 in C3]:
        # print((c1+c2+c3)/3 )
        if (c1+c2+c3)/3 <avg_current*1.1:
            count_policies+=1
            #print(count_policies)
            c4 = 0.2/(1/6 - (0.2/c1 + 0.2/c2 + 0.2/c3))
            policies[count,:] = [c1, c2, c3, c4]
            count += 1
            
            if c4 >= C4_LIMITS[0] and c4 <= C4_LIMITS[1]:
                if c1 == 4.8 and c2 == 4.8 and c3 == 4.8:
                    #print('baseline')
                    pass
                else:
                    valid_policies[valid_count,:] = [c1, c2, c3, c4]
                    valid_count += 1


    policies = policies[0:count]
    valid_policies = valid_policies[0:valid_count]

    #print('Count = ' + str(count))
    #print('Valid count = ' + str(valid_count))
    #print(os.getcwd())
    np.savetxt("data/policies_all.csv", valid_policies, delimiter=',', fmt='%1.3f')
    print("Final cost of the plan: ",avg_current)
    return avg_current

def closed_loop_opt(round_idx):
    class BayesGap(object):

        def __init__(self):
            policy_file='policies_all.csv'
            data_dir='data/'
            log_file='log.csv'
            arm_bounds_dir='bounds/'
            early_pred_dir='pred/'
            next_batch_dir='batch/'
            # round_idx=1

            seed=0
            budget=8
            bsize=220

            gamma=1
            likelihood_std=164
            init_beta=5
            epsilon=0.5

            standardization_mean=947.0
            standardization_std=164

            np.random.seed(0)
            np.set_printoptions(threshold=np.inf)
        

            self.policy_file = os.path.join(data_dir, policy_file)
            self.prev_arm_bounds_file = os.path.join(data_dir, arm_bounds_dir, str(round_idx-1) + '.pkl') # note this is for previous round
            self.prev_early_pred_file = os.path.join(data_dir, early_pred_dir, str(round_idx-1) + '.csv') # note this is for previous round
            self.arm_bounds_file = os.path.join(data_dir, arm_bounds_dir, str(round_idx) + '.pkl')
            self.next_batch_file = os.path.join(data_dir, next_batch_dir, str(round_idx) + '.csv')

            self.param_space = self.get_parameter_space()
            self.num_arms = self.param_space.shape[0]

            self.X = self.get_design_matrix(gamma)

            self.num_dims = self.X.shape[1]
            self.batch_size = bsize
            self.budget = budget
            self.round_idx = round_idx

            self.sigma = likelihood_std
            self.beta = init_beta
            self.epsilon = epsilon

            self.standardization_mean = standardization_mean
            self.standardization_std = standardization_std

            self.eta = self.standardization_std

            pass

        def get_design_matrix(self, gamma):

            from sklearn.kernel_approximation import (RBFSampler, Nystroem)
            param_space = self.param_space
            num_arms = self.num_arms

            feature_map_nystroem = Nystroem(gamma=gamma, n_components=num_arms, random_state=1)
            X = feature_map_nystroem.fit_transform(param_space)
            return X

        def run(self):

            prev_arm_bounds_file = self.prev_arm_bounds_file
            prev_early_pred_file = self.prev_early_pred_file
            arm_bounds_file = self.arm_bounds_file
            next_batch_file = self.next_batch_file

            num_arms = self.num_arms
            batch_size = self.batch_size
            epsilon = self.epsilon
            X = self.X
            round_idx = self.round_idx
            param_space = self.param_space

            def find_J_t(carms):

                B_k_ts = []
                for k in range(num_arms):
                    if k in carms:
                        temp_upper_bounds = np.delete(upper_bounds, k)
                        B_k_t = np.amax(temp_upper_bounds)
                        B_k_ts.append(B_k_t)
                    else:
                        B_k_ts.append(np.inf)

                B_k_ts = np.array(B_k_ts) - np.array(lower_bounds)
                J_t = np.argmin(B_k_ts)
                min_B_k_t = np.amin(B_k_ts)
                return J_t, min_B_k_t


            def find_j_t(carms, preselected_arm):

                U_k_ts = []
                for k in range(num_arms):
                    if k in carms and k != preselected_arm:
                        U_k_ts.append(upper_bounds[k])
                    else:
                        U_k_ts.append(-np.inf)

                j_t = np.argmax(np.array(U_k_ts))

                return j_t


            def get_confidence_diameter(k):

                return upper_bounds[k] - lower_bounds[k]

            if round_idx == 0:
                X_t = []
                Y_t = []
                proposal_arms = [] 
                proposal_gaps = []
                beta = self.beta
                upper_bounds, lower_bounds = self.get_posterior_bounds(beta)
                best_arm_params = None
            else:

                # load proposal_arms, proposal_gaps, X_t, Y_t, beta for previous round in bounds/<round_idx-1>.pkl
                with open(prev_arm_bounds_file, 'rb') as infile:
                    proposal_arms, proposal_gaps, X_t, Y_t, beta = pickle.load(infile)

                # update beta for this round
                beta = np.around(beta * epsilon, 4)

                # get armidx of batch policies and early predictions for previous round in pred/<round_idx-1>.csv

                with open(prev_early_pred_file, 'r', encoding='utf-8-sig') as infile:
                    reader = csv.reader(infile, delimiter=',')
                    early_pred = np.asarray([list(map(float, row)) for row in reader])
                #print('Early predictions')
                #print(early_pred)
                #print()
                #print('Standardized early predictions')
                early_pred[:, -1] = early_pred[:, -1] - self.standardization_mean
                #print(early_pred)

                batch_policies = early_pred[:, :3]
                batch_arms = [param_space.tolist().index(policy) for policy in batch_policies.tolist()]
                X_t.append(X[batch_arms])

                batch_rewards = early_pred[:, 4].reshape(-1, 1) # this corresponds to 5th column coz we are supposed to ignore the 4th column
                Y_t.append(batch_rewards)

                np_X_t = np.vstack(X_t)
                np_Y_t = np.vstack(Y_t)
                upper_bounds, lower_bounds = self.get_posterior_bounds(beta, np_X_t, np_Y_t)
                J_prev_round = proposal_arms[round_idx-1]
                temp_upper_bounds = np.delete(upper_bounds, J_prev_round)
                B_k_t = np.amax(temp_upper_bounds) - lower_bounds[J_prev_round]
                proposal_gaps.append(B_k_t)
                best_arm = proposal_arms[np.argmin(np.array(proposal_gaps))]
                best_arm_params = param_space[best_arm]

            #print('Arms with (non-standardized) upper bounds, lower bounds, and mean (upper+lower)/2lifetimes')
            nonstd_upper_bounds = upper_bounds+self.standardization_mean
            nonstd_lower_bounds = lower_bounds+self.standardization_mean
            for ((policy_id, policy_param), ub, lb, mean) in zip(enumerate(param_space), nonstd_upper_bounds, nonstd_lower_bounds, (nonstd_upper_bounds+nonstd_lower_bounds)/2):
                #print(policy_id, policy_param, ub, lb, mean, sep='\t')
                pass
            with open(arm_bounds_file[:-4]+'_bounds.pkl', 'wb') as outfile:
                pickle.dump([param_space, nonstd_upper_bounds, nonstd_lower_bounds, (nonstd_upper_bounds+nonstd_lower_bounds)/2], outfile)

            #print('Round', round_idx)
            #print('Current beta', beta)
            batch_arms = []
            candidate_arms = list(range(num_arms)) # an extension of Alg 1 to batch setting, don't select the arm again in same batch
            for batch_elem in range(batch_size):
                J_t, _ = find_J_t(candidate_arms)
                j_t = find_j_t(candidate_arms, J_t)
                s_J_t = get_confidence_diameter(J_t)
                s_j_t = get_confidence_diameter(j_t)
                a_t = J_t if s_J_t >= s_j_t else j_t

                if batch_elem == 0:
                    proposal_arms.append(J_t)
                batch_arms.append(a_t)
                candidate_arms.remove(a_t)

            #print('Policy indices selected for this round:', batch_arms)

            # save proposal_arms, proposal_gaps, X_t, Y_t, beta for current round in bounds/<round_idx>.pkl
            with open(arm_bounds_file, 'wb') as outfile:
                pickle.dump([proposal_arms, proposal_gaps, X_t, Y_t, beta], outfile)

            # save policies corresponding to batch_arms in batch/<round_idx>.csv
            batch_policies = [param_space[arm] for arm in batch_arms]
            with open(next_batch_file, 'w') as outfile:
                writer = csv.writer(outfile)
                writer.writerows(batch_policies)

            return best_arm_params

        def posterior_theta(self, X_t, Y_t):

            num_dims = self.num_dims
            sigma = self.sigma
            eta = self.eta
            prior_mean = np.zeros(num_dims)

            prior_theta_params = (prior_mean, eta * eta * np.identity(num_dims))

            if X_t is None:
                return prior_theta_params

            posterior_covar = np.linalg.inv(np.dot(X_t.T, X_t) / (sigma * sigma) + np.identity(num_dims) / (eta * eta))
            posterior_mean = np.linalg.multi_dot((posterior_covar, X_t.T, Y_t))/ (sigma * sigma)

            posterior_theta_params = (np.squeeze(posterior_mean), posterior_covar)
            return posterior_theta_params


        def marginal_mu(self, posterior_theta_params):

            X = self.X
            posterior_mean, posterior_covar = posterior_theta_params

            marginal_mean = np.dot(X, posterior_mean) 
            marginal_var = np.sum(np.multiply(np.dot(X, posterior_covar), X), 1)
            marginal_mu_params = (marginal_mean, marginal_var)

            return marginal_mu_params

        def get_posterior_bounds(self, beta, X=None, Y=None):
            """
            Returns upper and lower bounds for all arms at every time step.
            """

            posterior_theta_params = self.posterior_theta(X, Y)
            marginal_mu_params = self.marginal_mu(posterior_theta_params)
            marginal_mean, marginal_var = marginal_mu_params

            upper_bounds = marginal_mean + beta * np.sqrt(marginal_var)
            lower_bounds = marginal_mean - beta * np.sqrt(marginal_var)

            upper_bounds = np.around(upper_bounds, 4)
            lower_bounds = np.around(lower_bounds, 4)

            return (upper_bounds, lower_bounds)


        def get_parameter_space(self):

            policies = np.genfromtxt(self.policy_file,
                    delimiter=',', skip_header=0)
            np.random.shuffle(policies)

            return policies[:, :3]

    def main():

        policy_file='policies_all.csv'
        data_dir='data/'
        log_file='log.csv'
        arm_bounds_dir='bounds/'
        early_pred_dir='pred/'
        next_batch_dir='batch/'
        # round_idx=1

        seed=0
        budget=8
        bsize=220

        gamma=1
        likelihood_std=164
        init_beta=5
        epsilon=0.5

        standardization_mean=947.0
        standardization_std=164

        np.random.seed(0)
        np.set_printoptions(threshold=np.inf)
        
        #print(os.path.join(data_dir, arm_bounds_dir))

        assert (os.path.exists(os.path.join(data_dir, arm_bounds_dir)))
        assert (os.path.exists(os.path.join(data_dir, early_pred_dir)))
        assert (os.path.exists(os.path.join(data_dir, next_batch_dir)))

        agent = BayesGap()
        best_arm_params = agent.run()

        if round_idx != 0:
            #print('Best arm until round', round_idx-1, 'is', best_arm_params)
            lifetime_best_arm = sim(best_arm_params[0], best_arm_params[1], best_arm_params[2], variance=False)
            
            print('Lifetime of current best arm as per data simulator:', lifetime_best_arm)

        # Log the best arm at the end of each round
        log_path = os.path.join(data_dir, log_file)
        c4 = 0.2/(1/6 - (0.2/best_arm_params[0] + 0.2/best_arm_params[1] + 0.2/best_arm_params[2]))
        y=[best_arm_params[0],best_arm_params[0], best_arm_params[1], best_arm_params[2], c4]
        x=[0, 20, 40, 60, 80]
        if y is not None:
            with open('lifetime_best', 'wb') as fp:
                pickle.dump(y, fp)

        plt.figure()
        plt.step(x, y, label='Current')
        plt.grid(axis='x', color='0.95')
        # plt.legend(title='Protocols')
        plt.xlabel("SOC Percentage")
        plt.legend(title='Legend')
        # plt.ylabel("Current (A)")
        plt.title('Protocol'+' '+str(4-round_idx))
        plt.savefig('static\my_plot_'+str(round_idx)+'.png')

        with open(log_path, "a") as log_file:
            if round_idx == 0:
                log_file.write(str(init_beta)  + ',' +
                            str(gamma)      + ',' +
                            str(epsilon)    + ',' +
                            str(seed))
            elif round_idx == budget:
                    log_file.write(',' + str(lifetime_best_arm) + '\n')
            else:
                    log_file.write(',' + str(lifetime_best_arm))
    main()
