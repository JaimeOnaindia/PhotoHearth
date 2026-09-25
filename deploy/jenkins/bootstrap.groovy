import jenkins.model.Jenkins
import jenkins.model.JenkinsLocationConfiguration
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.model.Node
import hudson.slaves.DumbSlave
import hudson.slaves.JNLPLauncher
import hudson.slaves.RetentionStrategy
import hudson.plugins.git.GitSCM
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition

def instance = Jenkins.get()
instance.setNumExecutors(0)
if (!(instance.securityRealm instanceof HudsonPrivateSecurityRealm)) {
    def realm = new HudsonPrivateSecurityRealm(false)
    realm.createAccount('jaime', new File('/run/secrets/jenkins_password').text.trim())
    instance.setSecurityRealm(realm)
    def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
    strategy.setAllowAnonymousRead(false)
    instance.setAuthorizationStrategy(strategy)
}
JenkinsLocationConfiguration.get().setUrl(System.getenv('JENKINS_PUBLIC_URL'))
if (instance.getNode('photohearth-ci') == null) {
    def agent = new DumbSlave('photohearth-ci', '/home/jenkins/agent', new JNLPLauncher())
    agent.setNumExecutors(1)
    agent.setLabelString('photohearth-ci')
    agent.setMode(Node.Mode.EXCLUSIVE)
    agent.setRetentionStrategy(new RetentionStrategy.Always())
    instance.addNode(agent)
}
def secret = new File('/agent-config/secret')
secret.text = instance.getComputer('photohearth-ci').getJnlpMac()
secret.setReadable(false, false)
secret.setReadable(true, true)
secret.setWritable(false, false)
secret.setWritable(true, true)
if (instance.getItem('PhotoHearth') == null) {
    def job = instance.createProject(WorkflowJob, 'PhotoHearth')
    def scm = new GitSCM('https://github.com/JaimeOnaindia/PhotoHearth.git')
    scm.branches = [new hudson.plugins.git.BranchSpec('*/main')]
    job.setDefinition(new CpsScmFlowDefinition(scm, 'Jenkinsfile'))
    job.save()
}
instance.save()
