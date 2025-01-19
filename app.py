### Before running the code please install requirements.txt using the command
# pip install -r requirements.txt
# Also change the path in line 13 'sqlite:///{path_name}/instagram_clone.db'
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/apple/Desktop/deepsolv/instagram_clone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'INSTAGRAM_BACKEND_CLONE'

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Creating Tables
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100))
    bio = db.Column(db.String(250))
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy=True)
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy=True)

class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caption = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    music_url = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50))
    datetime_posted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='posts')

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    datetime_posted = db.Column(db.DateTime, default=datetime.utcnow)

# API Endpoints
# User Registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(username=data['username'], password=hashed_password, name=data.get('name', ''), bio=data.get('bio', ''))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully!'}), 201

#User Login

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({'access_token': access_token}), 200
    return jsonify({'message': 'Invalid credentials!'}), 401

#Create Posts with required details

@app.route('/create_post', methods=['POST'])
@jwt_required()
def create_post():
    data = request.get_json()
    user_id = get_jwt_identity()
    new_post = Post(
        caption=data['caption'],
        image_url=data['image_url'],
        music_url=data.get('music_url'),
        category=data['category'],
        user_id=user_id
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify({'message': 'Post created successfully!'}), 201

#View a user profile. 
@app.route('/profile/<int:user_id>', methods=['GET'])
def view_profile(user_id):
    user = User.query.get_or_404(user_id)
    user_data = {
        'username': user.username,
        'name': user.name,
        'bio': user.bio,
        'followers_count': len(user.followers),
        'following_count': len(user.following),
        'posts': [{'id': post.id, 'caption': post.caption, 'image_url': post.image_url, 'datetime_posted': post.datetime_posted} for post in user.posts]
    }
    return jsonify(user_data), 200

#Follow other users.
@app.route('/follow/<int:user_id>', methods=['POST'])
@jwt_required()
def follow_user(user_id):
    follower_id = get_jwt_identity()
    if follower_id == user_id:
        return jsonify({'message': 'You cannot follow yourself!'}), 400
    if Follow.query.filter_by(follower_id=follower_id, followed_id=user_id).first():
        return jsonify({'message': 'Already following this user!'}), 400
    new_follow = Follow(follower_id=follower_id, followed_id=user_id)
    db.session.add(new_follow)
    db.session.commit()
    return jsonify({'message': 'Followed successfully!'}), 200

#Get contents posted by the logged in user.
@app.route('/my_posts', methods=['GET'])
@jwt_required()
def get_my_posts():
    user_id = get_jwt_identity()
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.datetime_posted.desc()).all()
    result = [
        {'id': post.id, 'caption': post.caption, 'image_url': post.image_url, 'datetime_posted': post.datetime_posted}
        for post in posts
    ]
    return jsonify(result), 200

#Get contents posted by other users on the platform.
@app.route('/other_posts', methods=['GET'])
@jwt_required()
def get_other_posts():
    user_id = get_jwt_identity()
    posts = Post.query.filter(Post.user_id != user_id).order_by(Post.datetime_posted.desc()).all()
    result = [
        {'id': post.id, 'caption': post.caption, 'image_url': post.image_url, 'datetime_posted': post.datetime_posted}
        for post in posts
    ]
    return jsonify(result), 200

#Get details of a specific post

@app.route('/post/<int:post_id>', methods=['GET'])
def get_post_details(post_id):
    post = Post.query.get_or_404(post_id)
    likes_count = Like.query.filter_by(post_id=post_id).count()
    comments = Comment.query.filter_by(post_id=post_id).all()
    comments_data = [{'user_id': comment.user_id, 'comment': comment.text, 'datetime': comment.datetime_posted} for comment in comments]

    post_data = {
        'id': post.id,
        'caption': post.caption,
        'image_url': post.image_url,
        'posted_by': post.user.username,
        'datetime_posted': post.datetime_posted,
        'likes_count': likes_count,
        'comments_count': len(comments),
        'comments': comments_data
    }
    return jsonify(post_data), 200

#Like a post.

@app.route('/like/<int:post_id>', methods=['POST'])
@jwt_required()
def like_post(post_id):
    user_id = get_jwt_identity()
    existing_like = Like.query.filter_by(post_id=post_id, user_id=user_id).first()
    if existing_like:
        return jsonify({'message': 'You have already liked this post'}), 400

    new_like = Like(user_id=user_id, post_id=post_id)
    db.session.add(new_like)
    db.session.commit()
    return jsonify({'message': 'Post liked successfully'}), 201

#Get all users who liked a particular post

@app.route('/likes/<int:post_id>', methods=['GET'])
def get_likes(post_id):
    likes = Like.query.filter_by(post_id=post_id).all()
    users = [{'user_id': like.user_id, 'username': like.user.username} for like in likes]
    return jsonify(users), 200

#Comment on a post.

@app.route('/comment/<int:post_id>', methods=['POST'])
@jwt_required()
def comment_on_post(post_id):
    data = request.get_json()
    user_id = get_jwt_identity()
    new_comment = Comment(user_id=user_id, post_id=post_id, text=data['comment'])
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({'message': 'Comment added successfully'}), 201

#Get all users and their comments on a particular post.

@app.route('/comments/<int:post_id>', methods=['GET'])
def get_comments(post_id):
    comments = Comment.query.filter_by(post_id=post_id).all()
    result = [{'user_id': comment.user_id, 'username': comment.user.username, 'comment': comment.text, 'datetime': comment.datetime_posted} for comment in comments]
    return jsonify(result), 200

#Implement user feed, where a user can get a list of posts based on the users they follow, in a reverse chronological order (Latest post on top). This should be paginated.

@app.route('/feed', methods=['GET'])
@jwt_required()
def get_feed():
    user_id = get_jwt_identity()
    followed_users = [follow.followed_id for follow in Follow.query.filter_by(follower_id=user_id).all()]
    posts = Post.query.filter(Post.user_id.in_(followed_users)).order_by(Post.datetime_posted.desc()).all()
    page = int(request.args.get('page', 1))
    per_page = 10
    paginated_posts = posts[(page - 1) * per_page:page * per_page]
    feed = [{
        'id': post.id,
        'caption': post.caption,
        'image_url': post.image_url,
        'datetime_posted': post.datetime_posted,
        'user': post.user.username
    } for post in paginated_posts]
    return jsonify(feed), 200

if __name__ == '__main__':
    with app.app_context():  # Create an application context
        db.create_all()      # Ensure database tables are created within the app context
    app.run(debug=True)
